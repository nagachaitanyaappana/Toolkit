"""
Phone Number & Truecaller Lookup View for Toolkit GUI.
Validates numbers, detects carriers, locations, timezones,
offers 1-click WhatsApp opening, and queries Truecaller Caller ID & spam scores.
"""

import asyncio
from pathlib import Path

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import phonenumbers
from phonenumbers import PhoneNumberType, carrier, geocoder, number_type, timezone

from tools.phone_checker import (
    delete_truecaller_session,
    load_truecaller_session,
    save_truecaller_session,
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


class TruecallerQueryWorker(QThread):
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, number: str, country_code: str, installation_id: str):
        super().__init__()
        self.number = number
        self.country_code = country_code
        self.installation_id = installation_id

    def run(self):
        try:
            import truecallerpy

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            res = loop.run_until_complete(
                truecallerpy.search_phonenumber(self.number, self.country_code, self.installation_id)
            )
            loop.close()

            if res.get("status_code") == 200 and res.get("data"):
                data_list = res["data"].get("data", [])
                if data_list:
                    self.result_signal.emit(data_list[0])
                    return
            self.error_signal.emit("No Caller ID records found.")
        except Exception as exc:
            self.error_signal.emit(str(exc))


class PhoneView(QWidget):
    toast_requested = pyqtSignal(str, bool)
    log_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.worker: TruecallerQueryWorker | None = None
        self._init_ui()
        self._update_truecaller_status()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("📱 Phone Number & Truecaller Intelligence")
        title.setProperty("class", "ViewTitle")
        sub = QLabel("Validate international numbers, identify carriers, location, timezones, and Truecaller caller ID.")
        sub.setProperty("class", "ViewSubtitle")
        header_box.addWidget(title)
        header_box.addWidget(sub)
        layout.addLayout(header_box)

        # Input Card
        card = QFrame()
        card.setProperty("class", "CyberCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        card_title = QLabel("LOOKUP TARGET")
        card_title.setProperty("class", "CardTitle")
        card_layout.addWidget(card_title)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.region_combo = QComboBox()
        self.region_combo.addItems(["IN (+91)", "US (+1)", "GB (+44)", "CA (+1)", "AU (+61)", "DE (+49)", "SG (+65)"])
        self.region_combo.setFixedWidth(120)
        self.region_combo.setFixedHeight(38)
        input_row.addWidget(self.region_combo)

        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("Enter phone number (e.g. +91 98765 43210 or 9876543210)")
        self.number_input.setFixedHeight(38)
        self.number_input.returnPressed.connect(self._inspect_number)
        input_row.addWidget(self.number_input)

        self.lookup_btn = QPushButton("🔍 Inspect")
        self.lookup_btn.setProperty("class", "PrimaryBtn")
        self.lookup_btn.setFixedHeight(38)
        self.lookup_btn.clicked.connect(self._inspect_number)
        input_row.addWidget(self.lookup_btn)

        card_layout.addLayout(input_row)
        layout.addWidget(card)

        # Results Split Cards
        results_row = QHBoxLayout()
        results_row.setSpacing(16)

        # Left: Telecom / Carrier Card
        self.telecom_card = QFrame()
        self.telecom_card.setProperty("class", "CyberCard")
        telecom_layout = QVBoxLayout(self.telecom_card)
        telecom_layout.setContentsMargins(18, 16, 18, 16)
        telecom_layout.setSpacing(12)

        telecom_title = QLabel("📡 TELECOM & LOCATION METRICS")
        telecom_title.setProperty("class", "CardTitle")
        telecom_layout.addWidget(telecom_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        self.status_val = QLabel("Awaiting input...")
        self.status_val.setStyleSheet(f"color: {TEXT_MUTED}; font-weight: 700;")
        self.e164_val = QLabel("-")
        self.carrier_val = QLabel("-")
        self.location_val = QLabel("-")
        self.timezone_val = QLabel("-")
        self.type_val = QLabel("-")

        for label in (self.e164_val, self.carrier_val, self.location_val, self.timezone_val, self.type_val):
            label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 600;")

        grid.addWidget(QLabel("Validation:"), 0, 0)
        grid.addWidget(self.status_val, 0, 1)
        grid.addWidget(QLabel("E.164 Format:"), 1, 0)
        grid.addWidget(self.e164_val, 1, 1)
        grid.addWidget(QLabel("Carrier Operator:"), 2, 0)
        grid.addWidget(self.carrier_val, 2, 1)
        grid.addWidget(QLabel("Location / State:"), 3, 0)
        grid.addWidget(self.location_val, 3, 1)
        grid.addWidget(QLabel("Timezone:"), 4, 0)
        grid.addWidget(self.timezone_val, 4, 1)
        grid.addWidget(QLabel("Line Type:"), 5, 0)
        grid.addWidget(self.type_val, 5, 1)

        telecom_layout.addLayout(grid)
        telecom_layout.addStretch()

        self.wa_btn = QPushButton("💬 Open Direct WhatsApp")
        self.wa_btn.setProperty("class", "SecondaryBtn")
        self.wa_btn.setEnabled(False)
        self.wa_btn.clicked.connect(self._open_whatsapp)
        telecom_layout.addWidget(self.wa_btn)

        results_row.addWidget(self.telecom_card, 1)

        # Right: Truecaller Intelligence Card
        self.tc_card = QFrame()
        self.tc_card.setProperty("class", "CyberCard")
        tc_layout = QVBoxLayout(self.tc_card)
        tc_layout.setContentsMargins(18, 16, 18, 16)
        tc_layout.setSpacing(12)

        tc_header = QHBoxLayout()
        tc_title = QLabel("🛡️ TRUECALLER CALLER ID")
        tc_title.setProperty("class", "CardTitle")
        tc_header.addWidget(tc_title)
        tc_header.addStretch()

        self.tc_badge = QLabel("NOT LOGGED IN")
        self.tc_badge.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 700; background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 4px;"
        )
        tc_header.addWidget(self.tc_badge)
        tc_layout.addLayout(tc_header)

        tc_grid = QGridLayout()
        tc_grid.setHorizontalSpacing(14)
        tc_grid.setVerticalSpacing(10)

        self.tc_name_val = QLabel("-")
        self.tc_name_val.setStyleSheet(f"color: {ACCENT_EMERALD}; font-size: 15px; font-weight: 800;")
        self.tc_spam_val = QLabel("-")
        self.tc_email_val = QLabel("-")

        tc_grid.addWidget(QLabel("Caller Name:"), 0, 0)
        tc_grid.addWidget(self.tc_name_val, 0, 1)
        tc_grid.addWidget(QLabel("Spam Risk Score:"), 1, 0)
        tc_grid.addWidget(self.tc_spam_val, 1, 1)
        tc_grid.addWidget(QLabel("Associated Email:"), 2, 0)
        tc_grid.addWidget(self.tc_email_val, 2, 1)

        tc_layout.addLayout(tc_grid)
        tc_layout.addStretch()

        tc_actions = QHBoxLayout()
        self.tc_login_btn = QPushButton("Truecaller Auth")
        self.tc_login_btn.setProperty("class", "SecondaryBtn")
        self.tc_login_btn.clicked.connect(self._manage_truecaller_auth)
        tc_actions.addWidget(self.tc_login_btn)

        self.tc_query_btn = QPushButton("Query Truecaller")
        self.tc_query_btn.setProperty("class", "PrimaryBtn")
        self.tc_query_btn.setEnabled(False)
        self.tc_query_btn.clicked.connect(self._query_truecaller)
        tc_actions.addWidget(self.tc_query_btn)

        tc_layout.addLayout(tc_actions)

        results_row.addWidget(self.tc_card, 1)
        layout.addLayout(results_row)
        layout.addStretch()

        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll)

        self.current_parsed: phonenumbers.PhoneNumber | None = None

    def _update_truecaller_status(self):
        session = load_truecaller_session()
        if session:
            self.tc_badge.setText("AUTHENTICATED")
            self.tc_badge.setStyleSheet(
                f"color: {ACCENT_EMERALD}; font-size: 10px; font-weight: 700; background: rgba(0,255,157,0.15); border: 1px solid {ACCENT_EMERALD}; padding: 2px 8px; border-radius: 4px;"
            )
            self.tc_login_btn.setText("Logout Session")
            if self.current_parsed and phonenumbers.is_valid_number(self.current_parsed):
                self.tc_query_btn.setEnabled(True)
        else:
            self.tc_badge.setText("NOT LOGGED IN")
            self.tc_badge.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 700; background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 4px;"
            )
            self.tc_login_btn.setText("Set Installation ID")
            self.tc_query_btn.setEnabled(False)

    def _inspect_number(self):
        raw_number = self.number_input.text().strip()
        if not raw_number:
            self.toast_requested.emit("Please enter a phone number.", True)
            return

        region_code = self.region_combo.currentText()[:2]

        try:
            parsed = phonenumbers.parse(raw_number, region_code)
            self.current_parsed = parsed
            is_valid = phonenumbers.is_valid_number(parsed)

            if is_valid:
                self.status_val.setText("✓ VALID NUMBER")
                self.status_val.setStyleSheet(f"color: {ACCENT_EMERALD}; font-weight: 800;")
                self.e164_val.setText(phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164))
                self.carrier_val.setText(carrier.name_for_number(parsed, "en") or "Unknown / Landline")
                self.location_val.setText(geocoder.description_for_number(parsed, "en") or "Unknown Region")
                self.timezone_val.setText(", ".join(timezone.time_zones_for_number(parsed)) or "Unknown")

                nt = number_type(parsed)
                type_str = {
                    PhoneNumberType.MOBILE: "Mobile Cell",
                    PhoneNumberType.FIXED_LINE: "Fixed Landline",
                    PhoneNumberType.TOLL_FREE: "Toll-Free",
                    PhoneNumberType.VOIP: "VoIP Digital",
                }.get(nt, "Standard Line")
                self.type_val.setText(type_str)

                self.wa_btn.setEnabled(True)

                session = load_truecaller_session()
                if session:
                    self.tc_query_btn.setEnabled(True)
                
                self.toast_requested.emit("Phone number analyzed.", False)
            else:
                self.status_val.setText("✗ INVALID NUMBER")
                self.status_val.setStyleSheet(f"color: {ACCENT_ERROR}; font-weight: 800;")
                self.wa_btn.setEnabled(False)
                self.tc_query_btn.setEnabled(False)

        except Exception as exc:
            self.status_val.setText("✗ PARSE ERROR")
            self.status_val.setStyleSheet(f"color: {ACCENT_ERROR}; font-weight: 800;")
            self.toast_requested.emit(f"Error parsing number: {str(exc)}", True)

    def _open_whatsapp(self):
        if self.current_parsed:
            digits = f"{self.current_parsed.country_code}{self.current_parsed.national_number}"
            url = f"https://wa.me/{digits}"
            QDesktopServices.openUrl(QUrl(url))
            self.toast_requested.emit("Opening WhatsApp in browser...", False)

    def _manage_truecaller_auth(self):
        session = load_truecaller_session()
        if session:
            reply = QMessageBox.question(
                self, "Truecaller Logout", "Do you want to log out and remove saved Truecaller session?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                delete_truecaller_session()
                self._update_truecaller_status()
                self.toast_requested.emit("Truecaller session cleared.", False)
        else:
            # Simple dialog to enter installation ID
            from PyQt6.QtWidgets import QInputDialog
            inst_id, ok = QInputDialog.getText(
                self, "Truecaller Credentials",
                "Enter your Truecaller Installation ID:\n(Or login using CLI: python main.py --cli)"
            )
            if ok and inst_id.strip():
                save_truecaller_session(inst_id.strip())
                self._update_truecaller_status()
                self.toast_requested.emit("Truecaller session saved!", False)

    def _query_truecaller(self):
        if not self.current_parsed:
            return
        session = load_truecaller_session()
        if not session:
            return

        digits = str(self.current_parsed.national_number)
        country_code = phonenumbers.region_code_for_number(self.current_parsed) or "IN"
        inst_id = session.get("installation_id", "")

        self.tc_query_btn.setEnabled(False)
        self.tc_name_val.setText("Querying Truecaller...")

        self.worker = TruecallerQueryWorker(digits, country_code, inst_id)
        self.worker.result_signal.connect(self._on_tc_result)
        self.worker.error_signal.connect(self._on_tc_error)
        self.worker.start()

    def _on_tc_result(self, data: dict):
        self.tc_query_btn.setEnabled(True)
        name = data.get("name") or "No name registered"
        self.tc_name_val.setText(name)

        spam_score = data.get("spamScore", 0)
        spam_type = data.get("spamType", "")
        if spam_score > 0:
            self.tc_spam_val.setText(f"⚠️ {spam_score}% Risk ({spam_type or 'Reported'})")
            self.tc_spam_val.setStyleSheet(f"color: {ACCENT_WARN}; font-weight: 700;")
        else:
            self.tc_spam_val.setText("✓ 0% (Clean / No Reports)")
            self.tc_spam_val.setStyleSheet(f"color: {ACCENT_EMERALD}; font-weight: 700;")

        emails = data.get("internetAddresses", [])
        if emails:
            self.tc_email_val.setText(emails[0].get("id", "-"))
        else:
            self.tc_email_val.setText("-")

        self.toast_requested.emit(f"Caller identified: {name}", False)

    def _on_tc_error(self, err: str):
        self.tc_query_btn.setEnabled(True)
        self.tc_name_val.setText("No records found")
        self.toast_requested.emit(f"Truecaller: {err}", True)
