import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QPushButton, QFileDialog,
    QVBoxLayout, QWidget, QMessageBox, QLabel, QHBoxLayout, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
import dkim

class EmailDropBox(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setReadOnly(False)
        self.drop_handler = None

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith('.eml'):
                e.acceptProposedAction()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            f = e.mimeData().urls()[0].toLocalFile()
            if f.lower().endswith('.eml'):
                if self.drop_handler:
                    self.drop_handler(f)
            else:
                QMessageBox.warning(self, "Bad file", "Not an .eml file.")

class DKIMWin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DKIMCheck")
        self.setMinimumSize(800, 600)

        self.dropzone = EmailDropBox()
        self.dropzone.drop_handler = self.load_the_file

        self.info_lbl = QLabel("Please ensure the DKIM signature is included in the header of the .eml file.")
        self.info_lbl.setAlignment(Qt.AlignCenter)
        self.info_lbl.setStyleSheet("color: white;")
        self.info_lbl.setWordWrap(True)

        self.butt_open = QPushButton("Open .eml file")
        self.butt_open.clicked.connect(self.choose_file)

        self.butt_go = QPushButton("Check DKIM")
        self.butt_go.clicked.connect(self.validateeml)

        self.butt_clear = QPushButton("Clear")
        self.butt_clear.clicked.connect(self.clear_box)

        butts = QHBoxLayout()
        butts.addWidget(self.butt_open)
        butts.addWidget(self.butt_go)
        butts.addWidget(self.butt_clear)

        layout = QVBoxLayout()
        layout.addWidget(self.info_lbl)
        layout.addWidget(self.dropzone)
        layout.addLayout(butts)

        inner = QWidget()
        inner.setLayout(layout)
        self.setCentralWidget(inner)

        self.darkmode()

    def darkmode(self):
        p = QPalette()
        p.setColor(QPalette.Window, QColor("#2b2b2b"))
        p.setColor(QPalette.WindowText, Qt.white)
        p.setColor(QPalette.Base, QColor("#1e1e1e"))
        p.setColor(QPalette.Text, Qt.white)
        p.setColor(QPalette.Button, QColor("#f0f0f0"))
        p.setColor(QPalette.ButtonText, Qt.black)
        self.setPalette(p)
        self.dropzone.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: white; }")

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select .eml file", "", "EML Files (*.eml);;All Files (*)")
        if path:
            self.load_the_file(path)

    def load_the_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                stuff = f.read()
            self.dropzone.setPlainText(stuff)
        except Exception as prob:
            QMessageBox.critical(self, "Error opening file", f"{prob}")

    def clear_box(self):
        self.dropzone.clear()

    def validateeml(self):
        raw_text = self.dropzone.toPlainText()
        raw = raw_text.encode("utf-8")

        try:
            import email
            from email.parser import Parser

            parsed_msg = Parser().parsestr(raw_text)
            dkim_header = parsed_msg.get_all("DKIM-Signature")

            if not dkim_header:
                QMessageBox.critical(self, "DKIM Error", "No DKIM signature header found.")
                return

            dkim_raw = "\n".join(dkim_header)
            signed_headers = []
            for part in dkim_raw.split(";"):
                part = part.strip()
                if part.startswith("h="):
                    signed_headers = [h.strip().lower() for h in part[2:].split(":")]
                    break

            required = {"from", "to", "date", "subject"}
            missing = required - set(signed_headers)

            if dkim.verify(raw):
                if missing:
                    missing_caps = ", ".join(h.upper() for h in sorted(missing))
                    self.pop_msg("PARTIAL PASS",
                        f"The DKIM signature is valid, but the following headers were not signed:<br><br>{missing_caps}<br><br>It is unknown if these specific fields were altered.")
                else:
                    self.pop_msg("PASS",
                        "The DKIM signature is valid and the contents were not altered after the email was sent.<br><br>The FROM, TO, SUBJECT, and DATE fields were included in the signature and were not altered.")
            else:
                self.pop_msg("FAIL", "The DKIM signature is either invalid or the message has been modified.")
        except Exception as boo:
            QMessageBox.critical(self, "DKIM error", f"{boo}")

    def pop_msg(self, status, msg):
        dk_window = QDialog(self)
        dk_window.setWindowTitle("DKIM Result")
        dk_window.setMinimumWidth(350)

        lay = QVBoxLayout()
        msg = msg.replace("\n", "<br>")  # Just in case
        txt = QLabel(f"<div style='text-align:center;'><b>{status}</b><br><br>{msg}</div>")
        txt.setWordWrap(True)
        txt.setAlignment(Qt.AlignCenter)

        butt_ok = QPushButton("OK")
        butt_ok.clicked.connect(dk_window.accept)

        lay.addWidget(txt)
        lay.addWidget(butt_ok, alignment=Qt.AlignCenter)

        dk_window.setLayout(lay)
        dk_window.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DKIMWin()
    win.show()
    sys.exit(app.exec_())
