#!/usr/bin/env python3
"""
Feuerwehr Alarmfax-Drucker
Überwacht ein E-Mail-Postfach und druckt PDF-Anhänge
von autorisierten Absendern automatisch aus.
"""

import imaplib
import email
import os
import subprocess
import time
import logging
import configparser
import tempfile
import signal
import sys
from email.header import decode_header
from pathlib import Path


def setup_logging(log_file: str) -> logging.Logger:
    logger = logging.getLogger("feuerwehr-drucker")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Datei-Handler
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        pass  # Fallback auf Konsole

    # Konsole
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def decode_mime_header(value: str) -> str:
    decoded_parts = decode_header(value)
    result = ""
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += part
    return result


def get_sender_address(msg) -> str:
    from_header = msg.get("From", "")
    decoded = decode_mime_header(from_header)
    # E-Mail-Adresse aus "Name <adresse@domain.com>" extrahieren
    if "<" in decoded and ">" in decoded:
        return decoded[decoded.index("<") + 1 : decoded.index(">")].strip().lower()
    return decoded.strip().lower()


def print_pdf(pdf_path: str, printer_name: str, copies: int, logger: logging.Logger) -> bool:
    try:
        cmd = [
            "lp",
            "-d", printer_name,
            "-n", str(copies),
            "-o", "fit-to-page",
            pdf_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info(f"Druckauftrag gesendet: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"Druckfehler: {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Druckbefehl Timeout")
        return False
    except FileNotFoundError:
        logger.error("'lp' nicht gefunden - ist CUPS installiert? (sudo apt install cups)")
        return False


def process_email(msg, config: configparser.ConfigParser, logger: logging.Logger) -> int:
    """Verarbeitet eine E-Mail und druckt alle PDF-Anhänge. Gibt Anzahl gedruckter PDFs zurück."""
    printed = 0
    printer_name = config["printer"]["printer_name"]
    copies = int(config["printer"].get("copies", 1))

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition", ""))

        # PDF erkennen: entweder als attachment oder application/pdf
        is_pdf = (
            content_type == "application/pdf"
            or content_type == "application/octet-stream"
            and "attachment" in content_disposition
            and part.get_filename("").lower().endswith(".pdf")
        )

        if not is_pdf:
            filename = part.get_filename("")
            if filename and filename.lower().endswith(".pdf"):
                is_pdf = True

        if is_pdf:
            filename = part.get_filename("anhang.pdf")
            payload = part.get_payload(decode=True)

            if not payload:
                logger.warning(f"Leerer Anhang: {filename}")
                continue

            # PDF temporär speichern und drucken
            with tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix="alarm_", delete=False
            ) as tmp:
                tmp.write(payload)
                tmp_path = tmp.name

            logger.info(f"PDF-Anhang gefunden: {filename} ({len(payload)} Bytes)")

            try:
                if print_pdf(tmp_path, printer_name, copies, logger):
                    printed += 1
            finally:
                os.unlink(tmp_path)

    return printed


def check_emails(
    imap: imaplib.IMAP4_SSL,
    config: configparser.ConfigParser,
    logger: logging.Logger
) -> None:
    allowed_sender = config["filter"]["allowed_sender"].lower()
    mailbox = config["email"].get("mailbox", "INBOX")

    imap.select(mailbox)

    # Nur ungelesene E-Mails suchen
    status, message_ids = imap.search(None, "UNSEEN")
    if status != "OK":
        logger.error("Fehler beim Suchen nach E-Mails")
        return

    ids = message_ids[0].split()
    if not ids:
        return

    logger.info(f"{len(ids)} ungelesene E-Mail(s) gefunden")

    for msg_id in ids:
        status, data = imap.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)
        sender = get_sender_address(msg)
        subject = decode_mime_header(msg.get("Subject", "(kein Betreff)"))

        logger.info(f"E-Mail von: {sender} | Betreff: {subject}")

        if sender != allowed_sender:
            logger.info(f"Ignoriert - Absender nicht autorisiert: {sender}")
            # Als gelesen markieren, damit sie nicht erneut verarbeitet wird
            imap.store(msg_id, "+FLAGS", "\\Seen")
            continue

        logger.info(f"Autorisierter Absender erkannt - prüfe Anhänge...")
        count = process_email(msg, config, logger)

        if count > 0:
            logger.info(f"{count} PDF(s) erfolgreich zum Drucken gesendet")
        else:
            logger.warning("Keine PDF-Anhänge in der E-Mail gefunden")

        # Als gelesen markieren
        imap.store(msg_id, "+FLAGS", "\\Seen")


def connect_imap(config: configparser.ConfigParser, logger: logging.Logger) -> imaplib.IMAP4_SSL:
    server = config["email"]["imap_server"]
    port = int(config["email"].get("imap_port", 993))
    address = config["email"]["email_address"]
    password = config["email"]["email_password"]

    logger.info(f"Verbinde mit {server}:{port} ...")
    imap = imaplib.IMAP4_SSL(server, port)
    imap.login(address, password)
    logger.info("IMAP-Verbindung erfolgreich")
    return imap


def main():
    # Config laden
    config_path = Path(__file__).parent / "config.ini"
    if not config_path.exists():
        print(f"FEHLER: Konfigurationsdatei nicht gefunden: {config_path}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    log_file = config["general"].get("log_file", "/var/log/feuerwehr-drucker.log")
    logger = setup_logging(log_file)
    check_interval = int(config["general"].get("check_interval", 30))

    logger.info("=== Feuerwehr Alarmfax-Drucker gestartet ===")
    logger.info(f"Überwache Postfach: {config['email']['email_address']}")
    logger.info(f"Autorisierter Absender: {config['filter']['allowed_sender']}")
    logger.info(f"Drucker: {config['printer']['printer_name']}")
    logger.info(f"Prüfintervall: {check_interval}s")

    # Sauber beenden bei SIGTERM/SIGINT
    running = True
    def handle_signal(sig, frame):
        nonlocal running
        logger.info("Beenden angefordert...")
        running = False
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    imap = None

    while running:
        try:
            if imap is None:
                imap = connect_imap(config, logger)

            check_emails(imap, config, logger)

        except imaplib.IMAP4.abort:
            logger.warning("IMAP-Verbindung unterbrochen, verbinde neu...")
            imap = None
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP-Fehler: {e}")
            imap = None
            time.sleep(10)
        except OSError as e:
            logger.error(f"Netzwerkfehler: {e}")
            imap = None
            time.sleep(10)
        except Exception as e:
            logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
            imap = None
            time.sleep(10)

        if running:
            time.sleep(check_interval)

    if imap:
        try:
            imap.logout()
        except Exception:
            pass

    logger.info("Feuerwehr Alarmfax-Drucker beendet")


if __name__ == "__main__":
    main()
