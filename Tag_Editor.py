#!/usr/bin/env python3
import sys
import pathlib
import subprocess
import importlib.util
from typing import Optional, List, Set

def check_dependencies():
    """Check if PyQt6 is installed and offer to install if missing"""
    if importlib.util.find_spec("PyQt6") is None:
        print("PyQt6 is not installed. This application requires PyQt6 to run.")
        response = input("Would you like to install PyQt6 now? (y/n): ").strip().lower()
        if response == 'y':
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
                print("PyQt6 installed successfully!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error installing PyQt6: {e}")
                print("Please install PyQt6 manually using: pip install PyQt6")
                sys.exit(1)
        else:
            print("PyQt6 is required to run this application. Exiting.")
            sys.exit(1)
    return True

# Only import PyQt6 after checking dependencies
if check_dependencies():
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QTextEdit, QPushButton, QListWidget, QFileDialog,
        QScrollArea, QMessageBox, QStatusBar, QMenuBar, QMenu, QLineEdit,
        QGroupBox
    )
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QPixmap, QImage, QShortcut, QKeySequence

SUPPORTED_FORMATS: Set[str] = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
MAX_IMAGE_DIMENSION = 1024
FILE_LIST_WIDTH = 200

class TagEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_folder: Optional[pathlib.Path] = None
        self.current_image: Optional[pathlib.Path] = None
        self.unsaved_changes = False
        
        self.setWindowTitle("Image Tag Editor")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # Create and setup file list with fixed width
        file_list_group = QGroupBox("List -  Ctrl + ⬆️/⬇️")
        file_list_group.setFixedWidth(FILE_LIST_WIDTH)
        file_list_layout = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.itemSelectionChanged.connect(self.on_image_selected)
        file_list_layout.addWidget(self.file_list)
        file_list_group.setLayout(file_list_layout)
        main_layout.addWidget(file_list_group)
        
        # Create right side layout for image and text
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        # Create image group
        image_group = QGroupBox("Current Image")
        image_layout = QVBoxLayout()
        
        # Create scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(400)
        
        # Create image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        image_layout.addWidget(self.scroll_area)
        image_group.setLayout(image_layout)
        right_layout.addWidget(image_group, stretch=1)  # Give image area more stretch
        
        # Create tags group
        tags_group = QGroupBox("Tags - Ctrl + Enter to Save")
        tags_layout = QVBoxLayout()
        
        # Create text edit
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(100)
        self.text_edit.textChanged.connect(self.on_text_changed)
        # Prevent default Enter key behavior
        self.text_edit.setAcceptRichText(False)
        tags_layout.addWidget(self.text_edit)
        
        # Create buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_current_tags)
        button_layout.addWidget(self.save_button)
        
        self.apply_all_button = QPushButton("Apply to All")
        self.apply_all_button.clicked.connect(self.apply_to_all)
        button_layout.addWidget(self.apply_all_button)
        
        tags_layout.addLayout(button_layout)
        tags_group.setLayout(tags_layout)
        right_layout.addWidget(tags_group)
        
        # Create quick tag group
        quick_tag_group = QGroupBox("Quick Tag")
        quick_tag_layout = QVBoxLayout()
        
        # Create quick tag input
        self.quick_tag_input = QLineEdit()
        self.quick_tag_input.setPlaceholderText("Enter tag to append/prepend...")
        quick_tag_layout.addWidget(self.quick_tag_input)
        
        # Create quick tag buttons
        quick_tag_buttons = QHBoxLayout()
        
        self.append_button = QPushButton("Append")
        self.append_button.clicked.connect(lambda: self.modify_tags("append"))
        quick_tag_buttons.addWidget(self.append_button)
        
        self.prepend_button = QPushButton("Prepend")
        self.prepend_button.clicked.connect(lambda: self.modify_tags("prepend"))
        quick_tag_buttons.addWidget(self.prepend_button)
        
        self.append_all_button = QPushButton("Append to All")
        self.append_all_button.clicked.connect(lambda: self.modify_all_tags("append"))
        quick_tag_buttons.addWidget(self.append_all_button)
        
        self.prepend_all_button = QPushButton("Prepend to All")
        self.prepend_all_button.clicked.connect(lambda: self.modify_all_tags("prepend"))
        quick_tag_buttons.addWidget(self.prepend_all_button)
        
        quick_tag_layout.addLayout(quick_tag_buttons)
        quick_tag_group.setLayout(quick_tag_layout)
        right_layout.addWidget(quick_tag_group)
        
        main_layout.addLayout(right_layout)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
        # Setup shortcuts
        self.setup_shortcuts()
        
        # Initialize UI state
        self.update_ui_state(False)

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        if self.current_image:
            self.load_image(self.current_image)

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = file_menu.addAction("Open Folder")
        open_action.triggered.connect(self.open_folder)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

    def setup_shortcuts(self):
        # Save and next with Ctrl+Enter
        save_shortcut = QShortcut(QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Return), self)
        save_shortcut.activated.connect(self.save_and_next)
        
        # New line with Shift+Enter
        new_line_shortcut = QShortcut(QKeySequence(Qt.KeyboardModifier.ShiftModifier | Qt.Key.Key_Return), self.text_edit)
        new_line_shortcut.activated.connect(self.handle_shift_enter)
        
        # Navigation shortcuts with Ctrl+Up/Down when text_edit has focus
        ctrl_up_shortcut = QShortcut(QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Up), self.text_edit)
        ctrl_up_shortcut.activated.connect(self.navigate_previous)
        
        ctrl_down_shortcut = QShortcut(QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Down), self.text_edit)
        ctrl_down_shortcut.activated.connect(self.navigate_next)
        
        # Regular Up/Down navigation when text_edit doesn't have focus
        up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        up_shortcut.activated.connect(self.handle_up_key)
        
        down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        down_shortcut.activated.connect(self.handle_down_key)

    def update_ui_state(self, enabled: bool):
        """Enable or disable UI elements based on whether a folder is loaded"""
        self.text_edit.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.apply_all_button.setEnabled(enabled)
        self.file_list.setEnabled(enabled)
        self.quick_tag_input.setEnabled(enabled)
        self.append_button.setEnabled(enabled)
        self.prepend_button.setEnabled(enabled)
        self.append_all_button.setEnabled(enabled)
        self.prepend_all_button.setEnabled(enabled)

    def open_folder(self):
        """Open folder dialog and load images"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.current_folder = pathlib.Path(folder)
            self.load_files()

    def load_files(self):
        """Load all supported image files from the current folder"""
        if not self.current_folder:
            return
        
        self.file_list.clear()
        image_files = set()  # Use set to prevent duplicates
        
        # Collect all image files
        for ext in SUPPORTED_FORMATS:
            image_files.update(self.current_folder.glob(f"*{ext}"))
            image_files.update(self.current_folder.glob(f"*{ext.upper()}"))
        
        # Sort files alphanumerically
        image_files = sorted(image_files)
        
        # Check for missing txt files
        missing_txt = []
        for img_file in image_files:
            txt_file = img_file.with_suffix('.txt')
            if not txt_file.exists():
                missing_txt.append(txt_file)
        
        # Ask to create missing txt files
        if missing_txt:
            reply = QMessageBox.question(
                self,
                "Missing Text Files",
                f"Found {len(missing_txt)} missing text files. Create them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                for txt_file in missing_txt:
                    try:
                        txt_file.write_text("")
                    except Exception as e:
                        QMessageBox.warning(
                            self,
                            "Error",
                            f"Failed to create {txt_file.name}: {str(e)}"
                        )
        
        # Populate file list
        for img_file in image_files:
            self.file_list.addItem(img_file.name)
        
        if self.file_list.count() > 0:
            self.update_ui_state(True)
            self.file_list.setCurrentRow(0)
        else:
            self.update_ui_state(False)
            QMessageBox.information(
                self,
                "No Images",
                "No supported image files found in the selected folder."
            )

    def load_image(self, image_path: pathlib.Path):
        """Load and display an image, scaling it appropriately"""
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText("Failed to load image")
            return
        
        # Scale image to fit the view while maintaining aspect ratio
        scaled_pixmap = self.scale_pixmap(pixmap)
        self.image_label.setPixmap(scaled_pixmap)

    def scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """Scale pixmap to fit the scroll area while maintaining aspect ratio"""
        view_size = self.scroll_area.size()
        scaled_size = pixmap.size()
        
        # Scale to fit view while maintaining aspect ratio
        scaled_size.scale(
            min(view_size.width(), MAX_IMAGE_DIMENSION),
            min(view_size.height(), MAX_IMAGE_DIMENSION),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        
        return pixmap.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    def on_image_selected(self):
        """Handle image selection from the list"""
        if self.check_unsaved_changes():
            current_item = self.file_list.currentItem()
            if current_item:
                image_path = self.current_folder / current_item.text()
                self.current_image = image_path
                self.load_image(image_path)
                self.load_tags()
                self.unsaved_changes = False
                # Set focus to text edit with cursor at end
                self.focus_text_edit()

    def load_tags(self):
        """Load tags from the corresponding txt file"""
        if not self.current_image:
            return
        
        txt_path = self.current_image.with_suffix('.txt')
        try:
            content = txt_path.read_text()
            self.text_edit.setText(content)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to load tags from {txt_path.name}: {str(e)}"
            )

    def save_current_tags(self):
        """Save current tags to the txt file"""
        if not self.current_image:
            return
        
        txt_path = self.current_image.with_suffix('.txt')
        try:
            txt_path.write_text(self.text_edit.toPlainText())
            self.unsaved_changes = False
            self.statusBar().showMessage("Tags saved", 2000)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to save tags to {txt_path.name}: {str(e)}"
            )

    def save_and_next(self):
        """Save current tags and move to next image"""
        if self.text_edit.hasFocus():
            self.save_current_tags()
            self.navigate_next()
            self.focus_text_edit()

    def apply_to_all(self):
        """Apply current tags to all loaded images"""
        if not self.current_folder:
            return
        
        reply = QMessageBox.warning(
            self,
            "Confirm Apply to All",
            "This will overwrite all txt files with the current content. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            content = self.text_edit.toPlainText()
            for i in range(self.file_list.count()):
                img_path = self.current_folder / self.file_list.item(i).text()
                txt_path = img_path.with_suffix('.txt')
                try:
                    txt_path.write_text(content)
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Failed to update {txt_path.name}: {str(e)}"
                    )
            self.statusBar().showMessage("Applied tags to all files", 2000)

    def modify_tags(self, action: str):
        """Modify tags for current file"""
        if not self.current_image:
            return
        
        new_tag = self.quick_tag_input.text().strip()
        if not new_tag:
            return
        
        current_content = self.text_edit.toPlainText().strip()
        
        if current_content:
            if action == "append":
                new_content = f"{current_content}, {new_tag}"
            else:  # prepend
                new_content = f"{new_tag}, {current_content}"
        else:
            new_content = new_tag
        
        self.text_edit.setText(new_content)
        self.save_current_tags()
        self.statusBar().showMessage(f"Tag {action}ed", 2000)

    def modify_all_tags(self, action: str):
        """Modify tags for all files"""
        if not self.current_folder:
            return
        
        new_tag = self.quick_tag_input.text().strip()
        if not new_tag:
            return
        
        reply = QMessageBox.warning(
            self,
            f"Confirm {action.title()} to All",
            f"This will {action} the tag to all txt files. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for i in range(self.file_list.count()):
                img_path = self.current_folder / self.file_list.item(i).text()
                txt_path = img_path.with_suffix('.txt')
                try:
                    current_content = txt_path.read_text().strip()
                    if current_content:
                        if action == "append":
                            new_content = f"{current_content}, {new_tag}"
                        else:  # prepend
                            new_content = f"{new_tag}, {current_content}"
                    else:
                        new_content = new_tag
                    txt_path.write_text(new_content)
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Failed to update {txt_path.name}: {str(e)}"
                    )
            
            # Reload current file's tags
            self.load_tags()
            self.statusBar().showMessage(f"Tags {action}ed to all files", 2000)

    def on_text_changed(self):
        """Handle text changes in the editor"""
        self.unsaved_changes = True

    def check_unsaved_changes(self) -> bool:
        """Check for unsaved changes and prompt user to save if necessary"""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save changes before continuing?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.save_current_tags()
                return True
            elif reply == QMessageBox.StandardButton.No:
                return True
            else:
                return False
        return True

    def handle_shift_enter(self):
        """Handle Shift+Enter key press"""
        if self.text_edit.hasFocus():
            cursor = self.text_edit.textCursor()
            cursor.insertText('\n')

    def focus_text_edit(self):
        """Set focus to text edit and move cursor to end"""
        self.text_edit.setFocus()
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

    def handle_up_key(self):
        """Handle Up key press based on focus"""
        if not self.text_edit.hasFocus():
            self.navigate_previous()

    def handle_down_key(self):
        """Handle Down key press based on focus"""
        if not self.text_edit.hasFocus():
            self.navigate_next()

    def navigate_previous(self):
        """Navigate to previous image"""
        current_row = self.file_list.currentRow()
        if current_row > 0:
            self.file_list.setCurrentRow(current_row - 1)
            self.focus_text_edit()

    def navigate_next(self):
        """Navigate to next image"""
        current_row = self.file_list.currentRow()
        if current_row < self.file_list.count() - 1:
            self.file_list.setCurrentRow(current_row + 1)
            self.focus_text_edit()

def main():
    app = QApplication(sys.argv)
    window = TagEditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()