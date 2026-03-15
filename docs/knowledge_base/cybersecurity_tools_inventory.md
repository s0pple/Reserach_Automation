# 🛠️ Cybersecurity Tools Inventory (Fireship "Illegal Tools" Edition)

> **Die Bibel:** [Kali Linux Tools Documentation](https://www.kali.org/tools/) – Primäre Quelle für alle technischen Details und Manuals.

Diese Übersicht katalogisiert die im Video vorgestellten Tools und ordnet sie unserer Agenten-Strategie zu.

| # | Name | Kategorie (Tag) | Zweck (Video-Fokus) | Projekt-Integration | Phase | Priorität |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Nmap** | `[Layer:Recon]` | Netzwerk-Scanning, offene Ports finden. | Infrastruktur-Audit von Startups & Wettbewerbern. | 1 | Hoch |
| 2 | **Wireshark** | `[Layer:Forensics]` | Paket-Sniffer, Gespräche im Netzwerk belauschen. | Traffic-Analyse eigener Agenten (Debugging/Security). | 2 | Mittel |
| 3 | **Metasploit** | `[Layer:Exploit]` | Ausnutzen bekannter Schwachstellen (EternalBlue). | Simulation von Cyber-Angriffen auf eigene Systeme. | 4 | Niedrig |
| 4 | **Aircrack-ng** | `[Layer:Exploit]` | WLAN-Monitoring & Passwort-Knacken. | Physische Sicherheitsaudits (WLAN-Stärke-Check). | 4 | Niedrig |
| 5 | **Hashcat** | `[Layer:Forensics]` | Passwort-Knacken via GPU (Dictionary/Brute-Force). | Passwort-Auditing interner Datenbank-Dumps. | 3 | Mittel |
| 6 | **Skipfish** | `[Layer:Recon]` | Rekursiver Web-App-Scanner (XSS, SQLi). | Pre-Research Audit von Web-Applikationen. | 1 | Hoch |
| 7 | **Foremost** | `[Layer:Forensics]` | Datenrettung (File Carving) von Festplatten. | Rekonstruktion verlorener/korrupter Research-Dumps. | 2 | Hoch |
| 8 | **SQLMap** | `[Layer:Exploit]` | Automatisierte SQL-Injection & DB-Dumping. | Tiefenanalyse von Datenlecks bei Wettbewerbern. | 3 | Hoch |
| 9 | **hping3** | `[Layer:Recon]` | Netzwerk-Paket-Generator (DoS-Stresstests). | Load-Testing & Firewall-Bypass Simulationen. | 3 | Mittel |
| 10 | **SET** | `[Agent:CyberSec]` | Social Engineering (Phishing, Klonen von Seiten). | Security Awareness Training (Simulation). | 4 | Niedrig |

---

## 🏷️ Tag-Struktur & Definitionen

| Tag | Bedeutung | Zielgruppe |
| :--- | :--- | :--- |
| `[Layer:Recon]` | Informationsbeschaffung (Passiv/Aktiv) | Research-Agent, Venture Analyst |
| `[Layer:Exploit]` | Aktive Interaktion mit Sicherheitslücken | CyberSec Expert |
| `[Layer:Forensics]` | Analyse & Wiederherstellung von Daten | Data Engineer, Incident Response |
| `[Agent:CyberSec]` | Exklusive Tasks für den Sicherheits-Agenten | CyberSec Expert |
| `[Risk:High]` | Hohes Risiko für IP-Blocks oder rechtliche Grauzonen | Alle (Warnung!) |
