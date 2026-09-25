"""
Password Manager & Vault View for Toolkit GUI.
Features PBKDF2 AES-256 Fernet encryption, password generator,
searchable credential table, and 1-click clipboard integration.
"""

import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tools.password_mgr import (
    CONFIG_DIR,
    VAULT_FILE,
    derive_key,
    generate_random_password,
)
from ui.gui.theme import (
    ACCENT_CYAN,
    ACCENT_EMERALD,
    ACCENT_ERROR,
    ACCENT_WARN,
    BG_CARD,
    BG_INPUT,
    BORDER_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class AccountDialog(QDialog):
    """Dialog to create or edit an account entry."""

    def __init__(self, parent=None, account: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add / Edit Account" if not account else f"Edit {account.get('service')}")
        self.setFixedWidth(440)
        self.account = account or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Add New Credential" if not self.account else "Edit Credential")
        title.setProperty("class", "ViewTitle")
        layout.addWidget(title)

        # Service
        layout.addWidget(QLabel("Service / Website Name:"))
        self.service_input = QLineEdit(self.account.get("service", ""))
        self.service_input.setPlaceholderText("e.g. GitHub, Google, AWS")
        layout.addWidget(self.service_input)

        # Username
        layout.addWidget(QLabel("Username / Email:"))
        self.user_input = QLineEdit(self.account.get("username", ""))
        self.user_input.setPlaceholderText("e.g. user@example.com")
        layout.addWidget(self.user_input)

        # Password
        layout.addWidget(QLabel("Password:"))
        pw_box = QHBoxLayout()
        self.pw_input = QLineEdit(self.account.get("password", ""))
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        pw_box.addWidget(self.pw_input)

        gen_btn = QPushButton("🎲 Gen")
        gen_btn.setProperty("class", "SecondaryBtn")
        gen_btn.clicked.connect(self._generate_into_input)
        pw_box.addWidget(gen_btn)
        layout.addLayout(pw_box)

        # Notes
        layout.addWidget(QLabel("Notes (Optional):"))
        self.notes_input = QLineEdit(self.account.get("notes", ""))
        self.notes_input.setPlaceholderText("Additional notes or recovery hints")
        layout.addWidget(self.notes_input)

        layout.addSpacing(10)

        # Buttons
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Credential")
        save_btn.setProperty("class", "PrimaryBtn")
        save_btn.clicked.connect(self._validate_and_save)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _generate_into_input(self):
        pw = generate_random_password(length=20)
        self.pw_input.setText(pw)
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Normal)

    def _validate_and_save(self):
        if not self.service_input.text().strip():
            return
        self.account["service"] = self.service_input.text().strip()
        self.account["username"] = self.user_input.text().strip()
        self.account["password"] = self.pw_input.text()
        self.account["notes"] = self.notes_input.text().strip()
        self.accept()


class PasswordView(QWidget):
    toast_requested = pyqtSignal(str, bool)
    log_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.master_password: str | None = None
        self.vault_data: list[dict] = []
        self._init_ui()
        self._check_vault_status()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 28, 28, 28)
        self.main_layout.setSpacing(18)

        # ─── 1. LOCK / SETUP SCREEN CONTAINER ───
        self.lock_container = QFrame()
        self.lock_container.setProperty("class", "CyberCard")
        lock_layout = QVBoxLayout(self.lock_container)
        lock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_layout.setContentsMargins(40, 40, 40, 40)
        lock_layout.setSpacing(16)

        self.lock_icon = QLabel("🔐")
        self.lock_icon.setStyleSheet("font-size: 42px;")
        self.lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_layout.addWidget(self.lock_icon)

        self.lock_title = QLabel("Encrypted Password Vault")
        self.lock_title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {TEXT_PRIMARY};")
        self.lock_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_layout.addWidget(self.lock_title)

        self.lock_sub = QLabel("Enter your master password to decrypt your credentials.")
        self.lock_sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.lock_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_layout.addWidget(self.lock_sub)

        self.master_input = QLineEdit()
        self.master_input.setPlaceholderText("Master Password...")
        self.master_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_input.setFixedWidth(320)
        self.master_input.setFixedHeight(38)
        self.master_input.returnPressed.connect(self._unlock_or_setup)
        lock_layout.addWidget(self.master_input, alignment=Qt.AlignmentFlag.AlignCenter)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm Master Password...")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setFixedWidth(320)
        self.confirm_input.setFixedHeight(38)
        self.confirm_input.hide()
        lock_layout.addWidget(self.confirm_input, alignment=Qt.AlignmentFlag.AlignCenter)

        self.unlock_btn = QPushButton("Unlock Vault")
        self.unlock_btn.setProperty("class", "PrimaryBtn")
        self.unlock_btn.setFixedWidth(320)
        self.unlock_btn.setFixedHeight(38)
        self.unlock_btn.clicked.connect(self._unlock_or_setup)
        lock_layout.addWidget(self.unlock_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(self.lock_container)

        # ─── 2. UNLOCKED VAULT CONTAINER ───
        self.vault_container = QWidget()
        vault_layout = QVBoxLayout(self.vault_container)
        vault_layout.setContentsMargins(0, 0, 0, 0)
        vault_layout.setSpacing(16)

        # Header toolbar
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("🔐 Password Vault & Generator")
        title.setProperty("class", "ViewTitle")
        self.count_label = QLabel("0 credentials stored")
        self.count_label.setProperty("class", "ViewSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(self.count_label)
        header_row.addLayout(title_box)
        header_row.addStretch()

        lock_btn = QPushButton("🔒 Lock Vault")
        lock_btn.setProperty("class", "SecondaryBtn")
        lock_btn.clicked.connect(self._lock_vault)
        header_row.addWidget(lock_btn)

        add_btn = QPushButton("➕ Add Account")
        add_btn.setProperty("class", "PrimaryBtn")
        add_btn.clicked.connect(self._open_add_dialog)
        header_row.addWidget(add_btn)

        vault_layout.addLayout(header_row)

        # Generator & Search Row
        gen_card = QFrame()
        gen_card.setProperty("class", "CyberCard")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(16, 12, 16, 12)
        gen_layout.setSpacing(10)

        gen_title = QLabel("🎲 QUICK PASSWORD GENERATOR")
        gen_title.setProperty("class", "CardTitle")
        gen_layout.addWidget(gen_title)

        gen_controls = QHBoxLayout()
        gen_controls.setSpacing(12)

        self.gen_output = QLineEdit()
        self.gen_output.setReadOnly(True)
        self.gen_output.setPlaceholderText("Click Generate to create a strong password")
        self.gen_output.setFixedHeight(34)
        gen_controls.addWidget(self.gen_output, 3)

        self.slider_label = QLabel("Length: 18")
        self.slider_label.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: 700;")
        gen_controls.addWidget(self.slider_label)

        self.len_slider = QSlider(Qt.Orientation.Horizontal)
        self.len_slider.setRange(8, 64)
        self.len_slider.setValue(18)
        self.len_slider.setFixedWidth(120)
        self.len_slider.valueChanged.connect(lambda v: self.slider_label.setText(f"Length: {v}"))
        gen_controls.addWidget(self.len_slider)

        gen_action = QPushButton("Generate")
        gen_action.setProperty("class", "SecondaryBtn")
        gen_action.clicked.connect(self._generate_random)
        gen_controls.addWidget(gen_action)

        copy_gen_btn = QPushButton("Copy")
        copy_gen_btn.setProperty("class", "PrimaryBtn")
        copy_gen_btn.clicked.connect(self._copy_generated)
        gen_controls.addWidget(copy_gen_btn)

        gen_layout.addLayout(gen_controls)
        vault_layout.addWidget(gen_card)

        # Filter / Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search accounts, websites, or usernames...")
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self._filter_table)
        vault_layout.addWidget(self.search_input)

        # Accounts Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["SERVICE", "USERNAME / EMAIL", "PASSWORD", "NOTES", "ACTIONS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 160)
        self.table.verticalHeader().setVisible(False)
        vault_layout.addWidget(self.table)

        self.main_layout.addWidget(self.vault_container)
        self.vault_container.hide()

    def _check_vault_status(self):
        if not VAULT_FILE.exists():
            self.lock_title.setText("Setup Master Password")
            self.lock_sub.setText("Create a new master password to encrypt your local password vault.")
            self.confirm_input.show()
            self.unlock_btn.setText("Initialize Vault")
        else:
            self.lock_title.setText("Encrypted Password Vault")
            self.lock_sub.setText("Enter your master password to decrypt your credentials.")
            self.confirm_input.hide()
            self.unlock_btn.setText("Unlock Vault")

    def _unlock_or_setup(self):
        pw = self.master_input.text()
        if not pw:
            return

        if not VAULT_FILE.exists():
            # Setup
            conf = self.confirm_input.text()
            if pw != conf:
                self.toast_requested.emit("Master passwords do not match!", True)
                return
            if len(pw) < 4:
                self.toast_requested.emit("Password must be at least 4 characters.", True)
                return

            self.master_password = pw
            self.vault_data = []
            self._save_vault()
            self.toast_requested.emit("Vault created successfully!", False)
            self._transition_to_unlocked()
        else:
            # Unlock
            data = self._read_vault(pw)
            if data is not None:
                self.master_password = pw
                self.vault_data = data
                self.toast_requested.emit("Vault unlocked.", False)
                self.log_requested.emit("🔓 Password Vault unlocked successfully.")
                self._transition_to_unlocked()
            else:
                self.toast_requested.emit("Incorrect master password.", True)

    def _transition_to_unlocked(self):
        self.lock_container.hide()
        self.vault_container.show()
        self._render_table()
        self._generate_random()

    def _lock_vault(self):
        self.master_password = None
        self.vault_data = []
        self.master_input.clear()
        self.confirm_input.clear()
        self.vault_container.hide()
        self.lock_container.show()
        self.toast_requested.emit("Vault locked.", False)

    def _read_vault(self, master_password: str) -> list[dict] | None:
        try:
            with open(VAULT_FILE, "rb") as f:
                content = f.read()
            salt = content[:16]
            encrypted = content[16:]
            key = derive_key(master_password, salt)
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return None

    def _save_vault(self):
        if self.master_password is None:
            return
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        salt = os.urandom(16)
        key = derive_key(self.master_password, salt)
        fernet = Fernet(key)
        payload = json.dumps(self.vault_data, indent=2).encode("utf-8")
        encrypted = fernet.encrypt(payload)

        with open(VAULT_FILE, "wb") as f:
            f.write(salt + encrypted)
        try:
            os.chmod(VAULT_FILE, 0o600)
        except Exception:
            pass

    def _render_table(self):
        self.table.setRowCount(0)
        query = self.search_input.text().lower()

        filtered = [
            (idx, acc)
            for idx, acc in enumerate(self.vault_data)
            if query in acc.get("service", "").lower() or query in acc.get("username", "").lower()
        ]

        self.count_label.setText(f"{len(self.vault_data)} credentials saved")
        self.table.setRowCount(len(filtered))

        for row, (orig_idx, acc) in enumerate(filtered):
            # Service
            svc_item = QTableWidgetItem(acc.get("service", "Unknown"))
            svc_item.setForeground(Qt.GlobalColor.cyan)
            self.table.setItem(row, 0, svc_item)

            # Username
            self.table.setItem(row, 1, QTableWidgetItem(acc.get("username", "-")))

            # Password (masked by default)
            pw_item = QTableWidgetItem("••••••••••••")
            self.table.setItem(row, 2, pw_item)

            # Notes
            self.table.setItem(row, 3, QTableWidgetItem(acc.get("notes", "") or "-"))

            # Actions cell
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            copy_btn = QPushButton("📋")
            copy_btn.setToolTip("Copy Password")
            copy_btn.setProperty("class", "SecondaryBtn")
            copy_btn.setFixedHeight(26)
            copy_btn.clicked.connect(lambda _, p=acc.get("password", ""): self._copy_text(p, "Password"))
            actions_layout.addWidget(copy_btn)

            edit_btn = QPushButton("✏️")
            edit_btn.setToolTip("Edit Credential")
            edit_btn.setProperty("class", "SecondaryBtn")
            edit_btn.setFixedHeight(26)
            edit_btn.clicked.connect(lambda _, i=orig_idx: self._open_edit_dialog(i))
            actions_layout.addWidget(edit_btn)

            del_btn = QPushButton("🗑️")
            del_btn.setToolTip("Delete Credential")
            del_btn.setProperty("class", "DangerBtn")
            del_btn.setFixedHeight(26)
            del_btn.clicked.connect(lambda _, i=orig_idx: self._delete_account(i))
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 4, actions_widget)

    def _filter_table(self):
        self._render_table()

    def _copy_text(self, text: str, name: str = "Password"):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            self.toast_requested.emit(f"{name} copied to clipboard!", False)

    def _open_add_dialog(self):
        dlg = AccountDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.vault_data.append(dlg.account)
            self._save_vault()
            self._render_table()
            self.toast_requested.emit(f"Saved {dlg.account['service']}.", False)

    def _open_edit_dialog(self, index: int):
        if 0 <= index < len(self.vault_data):
            dlg = AccountDialog(self, account=dict(self.vault_data[index]))
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.vault_data[index] = dlg.account
                self._save_vault()
                self._render_table()
                self.toast_requested.emit("Account updated.", False)

    def _delete_account(self, index: int):
        if 0 <= index < len(self.vault_data):
            svc = self.vault_data[index].get("service", "account")
            reply = QMessageBox.question(
                self, "Confirm Delete", f"Are you sure you want to delete '{svc}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.vault_data.pop(index)
                self._save_vault()
                self._render_table()
                self.toast_requested.emit(f"Deleted {svc}.", False)

    def _generate_random(self):
        length = self.len_slider.value()
        pw = generate_random_password(length=length)
        self.gen_output.setText(pw)

    def _copy_generated(self):
        pw = self.gen_output.text()
        if pw:
            self._copy_text(pw, "Generated password")
