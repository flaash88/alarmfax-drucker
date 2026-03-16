# Feuerwehr Alarmfax-Drucker

Automatischer PDF-Drucker für Raspberry Pi: Überwacht ein E-Mail-Postfach und druckt PDF-Anhänge von autorisierten Absendern sofort aus — ohne manuellen Eingriff.

**Typischer Einsatz:** Alarmierungsmails vom Disponenten (z. B. `disponent@lfv.stmk.at`) werden automatisch auf dem Feuerwehrdrucker ausgegeben.

---

## Funktionsweise

1. Der Pi überwacht ein IMAP-Postfach im konfigurierten Intervall (Standard: 30 s)
2. Kommt eine ungelesene Mail vom autorisierten Absender an, werden **nur die PDF-Anhänge** gedruckt — kein E-Mail-Text, keine sonstigen Dateien
3. Die Mail wird als gelesen markiert und nicht erneut verarbeitet
4. Der Dienst läuft als systemd-Service und startet automatisch nach Stromausfall neu

---

## Voraussetzungen

| Was | Details |
|-----|---------|
| Hardware | Raspberry Pi (jedes Modell) + USB-Drucker |
| Betriebssystem | Raspberry Pi OS (Bookworm oder Bullseye) |
| E-Mail | IMAP-Zugang (Outlook/Office365, Gmail, GMX, …) |
| Python | Python 3 (vorinstalliert auf Raspberry Pi OS) |

---

## Installation

### 1. Dateien auf den Pi übertragen

```bash
scp -r feuerwehr-drucker/ pi@<IP-DES-PI>:/home/pi/
```

Oder per Git direkt auf dem Pi:

```bash
git clone https://github.com/flaash88/alarmfax-drucker.git
cd alarmfax-drucker
```

### 2. Abhängigkeiten installieren

```bash
sudo apt update
sudo apt install -y cups python3
sudo usermod -aG lpadmin pi
```

### 3. Drucker in CUPS einrichten

CUPS-Weboberfläche im Browser öffnen:
```
http://<IP-DES-PI>:631
```

→ **Administration → Drucker hinzufügen**

Druckernahmen kontrollieren — er muss `drucker-ff` heißen:
```bash
lpstat -p
```

> Anderen Druckernamen? In `config.ini` unter `printer_name` anpassen.

### 4. Konfiguration anlegen

```bash
cp config.example.ini config.ini
nano config.ini
```

Mindestens diese Felder ausfüllen:

```ini
[email]
imap_server   = outlook.office365.com   # siehe Tabelle unten
email_address = kdo.xxx@feuerwehr.at
email_password = DEIN_PASSWORT

[filter]
allowed_sender = disponent@lfv.stmk.at

[printer]
printer_name = drucker-ff
```

#### IMAP-Server häufiger Anbieter

| Anbieter | IMAP-Server |
|----------|-------------|
| Outlook / Office 365 | `outlook.office365.com` |
| Gmail | `imap.gmail.com` |
| GMX | `imap.gmx.net` |
| Web.de | `imap.web.de` |

#### Outlook mit MFA (Zwei-Faktor) — App-Passwort erstellen

1. [myaccount.microsoft.com/security-info](https://myaccount.microsoft.com/security-info) öffnen
2. **Anmeldemethode hinzufügen → App-Passwort**
3. Name: `Feuerwehr Pi`
4. Das generierte 16-stellige Passwort in `config.ini` eintragen

> **Wichtig:** IMAP muss im Konto aktiviert sein.
> Outlook Web: *Einstellungen → E-Mail → Synchronisieren → IMAP aktivieren*

### 5. Test

```bash
cd /home/pi/feuerwehr-drucker
python3 drucker.py
```

Jetzt eine Test-Mail mit PDF-Anhang vom autorisierten Absender schicken und den Log beobachten. Alles OK? Dann weiter.

### 6. Als Dienst einrichten (Autostart)

```bash
sudo cp feuerwehr-drucker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable feuerwehr-drucker
sudo systemctl start feuerwehr-drucker
```

---

## Betrieb & Überwachung

```bash
# Status prüfen
sudo systemctl status feuerwehr-drucker

# Live-Log verfolgen
sudo journalctl -u feuerwehr-drucker -f

# Dienst neu starten
sudo systemctl restart feuerwehr-drucker
```

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| `LOGIN failed` | App-Passwort verwenden; IMAP im Konto aktivieren |
| Drucker nicht gefunden | `lpstat -p` prüfen; CUPS-Setup wiederholen |
| PDF wird nicht gedruckt | `lp -d drucker-ff test.pdf` manuell testen |
| Dienst startet nicht | `journalctl -u feuerwehr-drucker` für Details |
| CUPS-Webseite nicht erreichbar | `sudo systemctl start cups` |

---

## Projektstruktur

```
feuerwehr-drucker/
├── drucker.py                  # Hauptskript
├── config.example.ini          # Konfigurationsvorlage (kein Passwort)
├── config.ini                  # Deine Konfiguration (nicht in Git!)
├── feuerwehr-drucker.service   # systemd-Dienstdatei
└── README.md
```

> `config.ini` ist in `.gitignore` eingetragen und wird **nie** ins Repository hochgeladen.

---

## Lizenz

MIT — frei verwendbar und anpassbar für andere Feuerwehren.
