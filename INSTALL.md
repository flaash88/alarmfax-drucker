# Feuerwehr Alarmfax-Drucker - Installation

## 1. Dateien auf den Raspberry Pi übertragen

```bash
scp -r feuerwehr-drucker/ pi@<IP-DES-PI>:/home/pi/
```

## 2. Abhängigkeiten installieren

```bash
sudo apt update
sudo apt install -y cups python3 python3-pip
sudo usermod -aG lpadmin pi
```

## 3. Drucker in CUPS einrichten

```bash
# CUPS-Weboberfläche öffnen (vom Browser im Netzwerk):
# http://<IP-DES-PI>:631

# Oder per Kommandozeile - USB-Drucker finden:
lpstat -v

# Drucker hinzufügen (Beispiel für HP):
# Im CUPS-Webinterface: Administration → Drucker hinzufügen

# Druckername prüfen:
lpstat -p
# → muss "drucker-ff" anzeigen
```

## 4. Konfiguration anpassen

```bash
nano /home/pi/feuerwehr-drucker/config.ini
```

Folgendes eintragen:
- `email_address` = deine Outlook-E-Mail-Adresse
- `email_password` = dein Passwort (siehe Hinweis unten)

### Outlook / Exchange Online - Passwort

**Option A: Normales Passwort** (wenn MFA deaktiviert)
→ Einfach das normale Passwort eintragen

**Option B: App-Passwort** (wenn MFA/2FA aktiviert ist)
1. Öffne: https://myaccount.microsoft.com/security-info
2. "Anmeldemethode hinzufügen" → "App-Passwort"
3. Name: "Feuerwehr Pi"
4. Generiertes 16-stelliges Passwort in config.ini eintragen

**Wichtig:** IMAP muss im Outlook/Exchange-Konto aktiviert sein!
- Outlook Web: Einstellungen → E-Mail → Synchronisieren → IMAP aktivieren
- Oder Admin aktiviert es im Exchange Admin Center

## 5. Skript testen

```bash
cd /home/pi/feuerwehr-drucker
python3 drucker.py
```

Jetzt eine Test-E-Mail mit PDF-Anhang von disponent@lfv.stmk.at schicken.
Log beobachten - alles OK? Dann weiter mit Schritt 6.

## 6. Als Dienst einrichten (automatischer Start)

```bash
sudo cp /home/pi/feuerwehr-drucker/feuerwehr-drucker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable feuerwehr-drucker
sudo systemctl start feuerwehr-drucker
```

## 7. Status prüfen

```bash
# Dienst-Status:
sudo systemctl status feuerwehr-drucker

# Live-Logs:
sudo journalctl -u feuerwehr-drucker -f

# Oder Log-Datei:
tail -f /home/pi/feuerwehr-drucker/feuerwehr-drucker.log
```

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| IMAP-Login schlägt fehl | App-Passwort verwenden, IMAP aktivieren |
| Drucker nicht gefunden | `lpstat -p` prüfen, CUPS-Setup wiederholen |
| PDF wird nicht gedruckt | `lp -d drucker-ff test.pdf` manuell testen |
| Dienst startet nicht | `journalctl -u feuerwehr-drucker` für Details |
