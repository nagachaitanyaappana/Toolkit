"""
Gmail & Message Dispatcher View for Toolkit GUI.
Send formatted emails and notifications with persistent Google App Password credentials,
dynamic template selection, multi-recipient broadcasting, repeat batch dispatching,
non-blocking SMTP transmission, and customizable scheduled/delayed delivery.
"""

from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re
import smtplib
import time

from PyQt6.QtCore import QDateTime, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tools.message_sender import (
    AUTH_FILE,
    TEMPLATES,
    delete_session,
    load_session,
    save_session,
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


def extract_emails(raw_text: str) -> list[str]:
    """Parse comma, semicolon, space, or newline separated email addresses."""
    parts = re.split(r"[,;\s\n]+", raw_text.strip())
    valid_emails = []
    seen = set()
    for p in parts:
        cleaned = p.strip()
        if "@" in cleaned and "." in cleaned and cleaned not in seen:
            seen.add(cleaned)
            valid_emails.append(cleaned)
    return valid_emails


class EmailSendWorker(QThread):
    progress_signal = pyqtSignal(int, int, str)  # completed, total, current_recipient
    finished_signal = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)

    def __init__(
        self,
        sender_email: str,
        app_password: str,
        recipients: list[str],
        subject: str,
        body: str,
        repeat_count: int = 1,
        interval_sec: float = 1.5,
    ):
        super().__init__()
        self.sender_email = sender_email
        self.app_password = app_password
        self.recipients = recipients
        self.subject = subject
        self.body = body
        self.repeat_count = max(1, repeat_count)
        self.interval_sec = interval_sec
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        clean_pw = self.app_password.replace(" ", "").strip()
        total_tasks = len(self.recipients) * self.repeat_count
        completed = 0

        self.log_signal.emit(
            f"⚡ Connecting to Gmail SMTP SSL for {len(self.recipients)} recipient(s) × {self.repeat_count} message(s) ({total_tasks} total)..."
        )

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
                server.login(self.sender_email, clean_pw)

                for r_idx in range(self.repeat_count):
                    for recipient in self.recipients:
                        if self._is_cancelled:
                            self.log_signal.emit("⏹ Batch transmission aborted by user.")
                            self.finished_signal.emit(False, "Transmission stopped by user.")
                            return

                        msg = MIMEMultipart()
                        msg["From"] = f"Toolkit <{self.sender_email}>"
                        msg["To"] = recipient

                        sub_text = self.subject
                        if self.repeat_count > 1:
                            sub_text = f"{self.subject} (#{r_idx + 1})"

                        msg["Subject"] = sub_text
                        msg.attach(MIMEText(self.body, "plain"))

                        server.sendmail(self.sender_email, recipient, msg.as_string())
                        completed += 1
                        self.progress_signal.emit(completed, total_tasks, recipient)
                        self.log_signal.emit(f"✓ [{completed}/{total_tasks}] Sent to {recipient}")

                        if completed < total_tasks and self.interval_sec > 0:
                            time.sleep(self.interval_sec)

            self.finished_signal.emit(True, f"All {completed} message(s) dispatched successfully!")
        except smtplib.SMTPAuthenticationError:
            self.log_signal.emit("✗ Authentication failed: Invalid Gmail address or Google App Password.")
            self.finished_signal.emit(False, "Authentication failed. Check App Password.")
        except Exception as exc:
            self.log_signal.emit(f"✗ SMTP transmission error: {str(exc)}")
            self.finished_signal.emit(False, str(exc))


class SenderAuthDialog(QDialog):
    def __init__(self, parent=None, current_email: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Configure Gmail Dispatcher")
        self.setFixedWidth(440)
        self.current_email = current_email
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Gmail Account Configuration")
        title.setProperty("class", "ViewTitle")
        layout.addWidget(title)

        info = QLabel(
            "Use your Gmail address and a 16-character Google App Password (myaccount.google.com/apppasswords)."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(info)

        layout.addWidget(QLabel("Gmail Address:"))
        self.email_input = QLineEdit(self.current_email)
        self.email_input.setPlaceholderText("your.email@gmail.com")
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("Google App Password:"))
        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("xxxx xxxx xxxx xxxx")
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pw_input)

        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save & Authenticate")
        save_btn.setProperty("class", "PrimaryBtn")
        save_btn.clicked.connect(self._validate_and_save)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _validate_and_save(self):
        email = self.email_input.text().strip()
        pw = self.pw_input.text().strip()
        if not email or not pw:
            return
        save_session(email, pw)
        self.accept()


class EmailView(QWidget):
    toast_requested = pyqtSignal(str, bool)
    log_requested = pyqtSignal(str)

    SCHEDULE_OPTIONS = [
        ("Send Immediately", 0),
        ("In 1 Minute", 60),
        ("In 5 Minutes", 300),
        ("In 15 Minutes", 900),
        ("In 30 Minutes", 1800),
        ("In 1 Hour", 3600),
        ("Custom Scheduled Time...", -1),
    ]

    INTERVAL_OPTIONS = [
        ("1.0 Second Delay", 1.0),
        ("2.0 Seconds Delay", 2.0),
        ("5.0 Seconds Delay", 5.0),
        ("10.0 Seconds Delay", 10.0),
        ("No Delay (Rapid)", 0.0),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.worker: EmailSendWorker | None = None
        self.scheduled_target: datetime | None = None
        self.schedule_timer = QTimer(self)
        self.schedule_timer.timeout.connect(self._on_schedule_tick)

        self._init_ui()
        self._refresh_session()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Responsive Scroll Area Wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # Header
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel("📨 Gmail & Message Dispatcher")
        title.setProperty("class", "ViewTitle")
        sub = QLabel(
            "Send single or multi-batch emails, broadcast to multiple recipients, or schedule delivery with Google App Passwords."
        )
        sub.setProperty("class", "ViewSubtitle")
        header_box.addWidget(title)
        header_box.addWidget(sub)
        layout.addLayout(header_box)

        # Account / Sender Status Bar Card
        account_card = QFrame()
        account_card.setProperty("class", "CyberCard")
        acc_layout = QHBoxLayout(account_card)
        acc_layout.setContentsMargins(16, 12, 16, 12)
        acc_layout.setSpacing(14)

        acc_layout.addWidget(QLabel("Active Sender:"))
        self.sender_label = QLabel("Not configured")
        self.sender_label.setStyleSheet(f"color: {ACCENT_EMERALD}; font-weight: 700;")
        acc_layout.addWidget(self.sender_label)

        acc_layout.addStretch()

        self.auth_btn = QPushButton("⚙️ Setup Sender")
        self.auth_btn.setProperty("class", "SecondaryBtn")
        self.auth_btn.clicked.connect(self._open_auth_dialog)
        acc_layout.addWidget(self.auth_btn)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setProperty("class", "DangerBtn")
        self.logout_btn.clicked.connect(self._logout)
        acc_layout.addWidget(self.logout_btn)

        layout.addWidget(account_card)

        # Message Compose Card
        compose_card = QFrame()
        compose_card.setProperty("class", "CyberCard")
        cmp_layout = QVBoxLayout(compose_card)
        cmp_layout.setContentsMargins(20, 20, 20, 20)
        cmp_layout.setSpacing(14)

        cmp_title = QLabel("DISPATCH MESSAGE")
        cmp_title.setProperty("class", "CardTitle")
        cmp_layout.addWidget(cmp_title)

        # Template Picker
        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(QLabel("Quick Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItem("Custom Blank Message", "")
        for t in TEMPLATES:
            self.template_combo.addItem(t["name"], t["body"])
        self.template_combo.currentIndexChanged.connect(self._apply_template)
        self.template_combo.setFixedHeight(34)
        tmpl_row.addWidget(self.template_combo)
        cmp_layout.addLayout(tmpl_row)

        # Recipient & Subject Row
        fields_grid = QVBoxLayout()
        fields_grid.setSpacing(10)

        # Recipient Input (Supports single or multiple emails)
        to_header = QHBoxLayout()
        to_header.addWidget(QLabel("Recipient Email(s):"))
        self.recipient_count_badge = QLabel("0 recipients")
        self.recipient_count_badge.setStyleSheet(
            f"color: {ACCENT_CYAN}; font-size: 11px; font-weight: 700;"
        )
        to_header.addStretch()
        to_header.addWidget(self.recipient_count_badge)
        fields_grid.addLayout(to_header)

        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText(
            "Enter emails separated by comma or space (e.g., user1@gmail.com, user2@gmail.com)"
        )
        self.to_input.setFixedHeight(36)
        self.to_input.textChanged.connect(self._update_counts)
        fields_grid.addWidget(self.to_input)

        # Subject
        sub_box = QVBoxLayout()
        sub_box.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Subject line...")
        self.subject_input.setFixedHeight(36)
        sub_box.addWidget(self.subject_input)
        fields_grid.addLayout(sub_box)

        cmp_layout.addLayout(fields_grid)

        # Body
        cmp_layout.addWidget(QLabel("Message Body:"))
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Type your email message here...")
        self.body_input.setFixedHeight(120)
        cmp_layout.addWidget(self.body_input)

        # ─── Multi-Message & Batch Count Settings Card ───
        batch_frame = QFrame()
        batch_frame.setStyleSheet(
            f"background: rgba(255, 255, 255, 0.02); border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 10px;"
        )
        batch_layout = QVBoxLayout(batch_frame)
        batch_layout.setContentsMargins(10, 8, 10, 8)
        batch_layout.setSpacing(8)

        batch_header = QHBoxLayout()
        batch_title = QLabel("🔢 MULTI-MESSAGE & BATCH SETTINGS:")
        batch_title.setStyleSheet(
            f"color: {ACCENT_CYAN}; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;"
        )
        batch_header.addWidget(batch_title)
        batch_header.addStretch()

        self.total_summary_badge = QLabel("Total: 0 messages")
        self.total_summary_badge.setStyleSheet(
            f"color: {ACCENT_EMERALD}; font-weight: 800; font-size: 11px;"
        )
        batch_header.addWidget(self.total_summary_badge)
        batch_layout.addLayout(batch_header)

        batch_controls = QHBoxLayout()
        batch_controls.setSpacing(16)

        # Repeat count / Message quantity spinbox
        rep_box = QHBoxLayout()
        rep_box.addWidget(QLabel("Quantity / Repeats:"))
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 100)
        self.repeat_spin.setValue(1)
        self.repeat_spin.setFixedHeight(32)
        self.repeat_spin.setFixedWidth(70)
        self.repeat_spin.valueChanged.connect(self._update_counts)
        rep_box.addWidget(self.repeat_spin)
        batch_controls.addLayout(rep_box)

        # Interval between messages
        int_box = QHBoxLayout()
        int_box.addWidget(QLabel("Interval Delay:"))
        self.interval_combo = QComboBox()
        for label, sec in self.INTERVAL_OPTIONS:
            self.interval_combo.addItem(label, sec)
        self.interval_combo.setFixedHeight(32)
        int_box.addWidget(self.interval_combo)
        batch_controls.addLayout(int_box)

        batch_layout.addLayout(batch_controls)
        cmp_layout.addWidget(batch_frame)

        # ─── Scheduled Delivery / Send Time Dropdown ───
        time_container = QFrame()
        time_container.setStyleSheet(
            f"background: rgba(255, 255, 255, 0.02); border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 10px;"
        )
        time_layout = QVBoxLayout(time_container)
        time_layout.setContentsMargins(10, 8, 10, 8)
        time_layout.setSpacing(8)

        time_header = QHBoxLayout()
        time_lbl = QLabel("⏰ DELIVERY TIMING:")
        time_lbl.setStyleSheet(
            f"color: {ACCENT_CYAN}; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;"
        )
        time_header.addWidget(time_lbl)

        self.schedule_combo = QComboBox()
        for label, seconds in self.SCHEDULE_OPTIONS:
            self.schedule_combo.addItem(label, seconds)
        self.schedule_combo.setFixedHeight(34)
        self.schedule_combo.currentIndexChanged.connect(self._on_schedule_changed)
        time_header.addWidget(self.schedule_combo, 1)

        time_layout.addLayout(time_header)

        # Custom DateTime row (hidden by default)
        self.custom_time_row = QHBoxLayout()
        self.custom_time_row.addWidget(QLabel("Choose Date & Time:"))
        self.custom_datetime = QDateTimeEdit()
        self.custom_datetime.setCalendarPopup(True)
        self.custom_datetime.setDateTime(QDateTime.currentDateTime().addSecs(600))
        self.custom_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.custom_datetime.setFixedHeight(34)
        self.custom_time_row.addWidget(self.custom_datetime, 1)
        time_layout.addLayout(self.custom_time_row)
        self.custom_datetime.hide()

        # Scheduled countdown banner
        self.countdown_banner = QFrame()
        self.countdown_banner.setStyleSheet(
            f"background: rgba(0, 229, 255, 0.08); border: 1px solid {ACCENT_CYAN}; border-radius: 6px; padding: 8px;"
        )
        cb_layout = QHBoxLayout(self.countdown_banner)
        cb_layout.setContentsMargins(8, 4, 8, 4)

        self.countdown_label = QLabel("⏳ Scheduled: Sending in ...")
        self.countdown_label.setStyleSheet(
            f"color: {ACCENT_CYAN}; font-weight: 700; font-size: 12px;"
        )
        cb_layout.addWidget(self.countdown_label)
        cb_layout.addStretch()

        self.cancel_schedule_btn = QPushButton("Cancel Scheduled Send")
        self.cancel_schedule_btn.setProperty("class", "DangerBtn")
        self.cancel_schedule_btn.setFixedHeight(28)
        self.cancel_schedule_btn.clicked.connect(self._cancel_schedule)
        cb_layout.addWidget(self.cancel_schedule_btn)

        time_layout.addWidget(self.countdown_banner)
        self.countdown_banner.hide()

        cmp_layout.addWidget(time_container)

        # ─── Live Transmission Progress Row ───
        self.progress_container = QWidget()
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(6)

        self.batch_progress_bar = QProgressBar()
        self.batch_progress_bar.setFixedHeight(12)
        self.batch_progress_bar.setValue(0)
        prog_layout.addWidget(self.batch_progress_bar)

        prog_status_row = QHBoxLayout()
        self.batch_status_label = QLabel("Ready to transmit.")
        self.batch_status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        prog_status_row.addWidget(self.batch_status_label)
        prog_status_row.addStretch()

        self.stop_btn = QPushButton("Stop Transmission")
        self.stop_btn.setProperty("class", "DangerBtn")
        self.stop_btn.setFixedHeight(24)
        self.stop_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self.stop_btn.clicked.connect(self._stop_transmission)
        prog_status_row.addWidget(self.stop_btn)
        prog_layout.addLayout(prog_status_row)

        cmp_layout.addWidget(self.progress_container)
        self.progress_container.hide()

        # Send Action Button
        cmp_layout.addSpacing(4)
        self.send_btn = QPushButton("🚀 TRANSMIT MESSAGES")
        self.send_btn.setProperty("class", "PrimaryBtn")
        self.send_btn.setFixedHeight(44)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send_clicked)
        cmp_layout.addWidget(self.send_btn)

        layout.addWidget(compose_card)
        layout.addStretch()

        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll)

    def _update_counts(self):
        emails = extract_emails(self.to_input.text())
        repeats = self.repeat_spin.value()
        total = len(emails) * repeats

        self.recipient_count_badge.setText(f"{len(emails)} recipient{'s' if len(emails) != 1 else ''}")
        self.total_summary_badge.setText(f"Total: {len(emails)} × {repeats} = {total} message{'s' if total != 1 else ''}")
        self.send_btn.setText(f"🚀 TRANSMIT {total} MESSAGE{'S' if total != 1 else ''}" if total > 1 else "🚀 TRANSMIT MESSAGE")

    def _refresh_session(self):
        session = load_session()
        if session:
            self.sender_label.setText(session.get("email", "Configured"))
            self.auth_btn.setText("Change Account")
            self.logout_btn.show()
            self.send_btn.setEnabled(True)
        else:
            self.sender_label.setText("No account configured")
            self.auth_btn.setText("⚙️ Setup Sender")
            self.logout_btn.hide()
            self.send_btn.setEnabled(False)

    def _open_auth_dialog(self):
        session = load_session()
        current_email = session.get("email", "") if session else ""
        dlg = SenderAuthDialog(self, current_email=current_email)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_session()
            self.toast_requested.emit("Gmail credentials configured.", False)

    def _logout(self):
        reply = QMessageBox.question(
            self,
            "Logout",
            "Remove saved email credentials?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_session()
            self._refresh_session()
            self.toast_requested.emit("Email credentials removed.", False)

    def _apply_template(self, index: int):
        body = self.template_combo.currentData()
        name = self.template_combo.currentText()
        if body:
            self.body_input.setText(body)
            self.subject_input.setText(f"Notification: {name}")

    def _on_schedule_changed(self, index: int):
        val = self.schedule_combo.currentData()
        if val == -1:
            self.custom_time_row.widget = self.custom_datetime.show()
            self.custom_datetime.setDateTime(QDateTime.currentDateTime().addSecs(600))
        else:
            self.custom_datetime.hide()

    def _on_send_clicked(self):
        session = load_session()
        if not session:
            self.toast_requested.emit("Configure sender email first.", True)
            return

        recipients = extract_emails(self.to_input.text())
        subject = self.subject_input.text().strip()
        body = self.body_input.toPlainText().strip()

        if not recipients:
            self.toast_requested.emit("Please enter at least one valid recipient email.", True)
            return
        if not body:
            self.toast_requested.emit("Message body cannot be empty.", True)
            return

        sec_delay = self.schedule_combo.currentData()

        if sec_delay == 0:
            # Immediate dispatch
            self._execute_batch_send(session, recipients, subject, body)
        elif sec_delay > 0:
            # Delay in seconds
            self.scheduled_target = datetime.now() + timedelta(seconds=sec_delay)
            self._start_countdown()
        else:
            # Custom datetime
            qdt = self.custom_datetime.dateTime()
            target = qdt.toPyDateTime()
            now = datetime.now()
            if target <= now:
                self.toast_requested.emit("Scheduled time must be in the future.", True)
                return
            self.scheduled_target = target
            self._start_countdown()

    def _start_countdown(self):
        self.send_btn.setEnabled(False)
        self.schedule_combo.setEnabled(False)
        self.custom_datetime.setEnabled(False)
        self.countdown_banner.show()
        self.schedule_timer.start(1000)
        self._on_schedule_tick()
        self.toast_requested.emit("Message batch scheduled for delayed delivery.", False)
        self.log_requested.emit(
            f"⏰ Batch scheduled for delivery at {self.scheduled_target.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _on_schedule_tick(self):
        if not self.scheduled_target:
            self._cancel_schedule()
            return

        now = datetime.now()
        diff = (self.scheduled_target - now).total_seconds()

        if diff <= 0:
            self.schedule_timer.stop()
            self.countdown_banner.hide()
            self.schedule_combo.setEnabled(True)
            self.custom_datetime.setEnabled(True)

            session = load_session()
            if session:
                recipients = extract_emails(self.to_input.text())
                subject = self.subject_input.text().strip()
                body = self.body_input.toPlainText().strip()
                self.log_requested.emit("⏰ Scheduled time reached. Transmitting batch...")
                self._execute_batch_send(session, recipients, subject, body)
            return

        m, s = divmod(int(diff), 60)
        h, m = divmod(m, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
        self.countdown_label.setText(
            f"⏳ Scheduled: Dispatching in {time_str} (at {self.scheduled_target.strftime('%H:%M:%S')})"
        )

    def _cancel_schedule(self):
        self.schedule_timer.stop()
        self.scheduled_target = None
        self.countdown_banner.hide()
        self.send_btn.setEnabled(True)
        self.schedule_combo.setEnabled(True)
        self.custom_datetime.setEnabled(True)
        self.toast_requested.emit("Scheduled dispatch cancelled.", False)
        self.log_requested.emit("Scheduled dispatch cancelled by user.")

    def _execute_batch_send(self, session: dict, recipients: list[str], subject: str, body: str):
        repeats = self.repeat_spin.value()
        interval = self.interval_combo.currentData()

        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ TRANSMITTING BATCH...")
        self.progress_container.show()
        self.batch_progress_bar.setValue(0)
        self.batch_status_label.setText(f"Starting batch dispatch (0 of {len(recipients) * repeats})...")

        self.worker = EmailSendWorker(
            sender_email=session["email"],
            app_password=session["app_password"],
            recipients=recipients,
            subject=subject,
            body=body,
            repeat_count=repeats,
            interval_sec=interval,
        )
        self.worker.progress_signal.connect(self._on_worker_progress)
        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.finished_signal.connect(self._on_batch_finished)
        self.worker.start()

    def _stop_transmission(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.batch_status_label.setText("Cancelling transmission...")

    def _on_worker_progress(self, current: int, total: int, recipient: str):
        pct = int(current * 100 / total) if total > 0 else 0
        self.batch_progress_bar.setValue(pct)
        self.batch_status_label.setText(f"Dispatched {current} of {total} messages ({pct}%) -> {recipient}")

    def _on_batch_finished(self, success: bool, msg: str):
        self.send_btn.setEnabled(True)
        self._update_counts()

        if success:
            self.batch_progress_bar.setValue(100)
            self.batch_status_label.setText(f"✓ {msg}")
            self.toast_requested.emit(msg, False)
        else:
            self.batch_status_label.setText(f"✗ Failed: {msg}")
            self.toast_requested.emit(f"Error: {msg}", True)
