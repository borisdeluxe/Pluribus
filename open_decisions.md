# Offene Entscheidungen

Status-Tracking fuer die TK14-Ausarbeitung. Abgearbeitete Punkte werden nach `decisions.md` uebertragen.

---

## Erledigt

- [x] **Infrastruktur: Server-Wahl** → CAX31 (siehe decisions.md)
- [x] **Lokale LLMs ja/nein** → Nein in Phase 1 (siehe decisions.md)

---

## Offen — Naechste Session

### 2. Staging-Server
- Eigener Hetzner CPX11 (€4/Monat) fuer Staging?
- Oder Staging auf dem Agency-Host (CAX31)?
- Oder kein Staging — Agency erstellt nur PRs, Deploy manuell?
- Empfehlung war: CPX11 separat, aber bei CAX31 mit 16 GB ggf. auch auf demselben Host moeglich.

### 3. Prod-Deploy-Strategie
- Manueller Prod-Deploy (L3) oder Time-Locked Auto-Deploy (L4)?
- Empfehlung: L3 (manuell), passt zu Boris' Anforderung "erst auf Zuruf".

### 4. Task-Intake-Granularitaet
- Jedes GitHub-Issue ein Pipeline-Run oder Batching?
- Empfehlung: Pro Issue sofort, wegen schnellerem Feedback.

### 5. Fast-Lane-Schwellwert
- Ab welchem Diff-Umfang greift der volle Agenten-Prozess (alle 7 Rollen)?
- Empfehlung: >30 LOC oder neuer Endpoint oder Migration → voller Prozess. Darunter → verkuerzte Pipeline (nur Implementer + QA).

### 6. Test-Designer vs. Implementer Boundary
- Darf der Implementer-Agent Tests aendern die der Test-Designer geschrieben hat?
- Empfehlung: Nein, ausser der Test ist nachweislich falsch (Gate-Check).

### 7. Containerisierung vs. Linux-User
- Docker/Podman pro Agent oder nur Linux-User-Trennung auf dem Server?
- Empfehlung: Linux-User fuer den Start, Container spaeter bei Bedarf.

### 8. Conductor-Ersatz auf Server
- Conductor (Melty Labs) ist ein Desktop-Tool (Mac). Was ersetzt es auf dem Agency-Server?
- Empfehlung: Claude Code CLI headless + tmux + eigenes Dispatch-Script.

### 9. Slack-Workspace
- Eigenes Slack-Workspace fuer Agency oder bestehender Workspace (Eurotext/Falara)?
- Empfehlung: Eigener Workspace oder separater Private Channel.

### 10. Reports-Aufbewahrung
- Wie lange werden Daily/Weekly Reports aufbewahrt?
- Empfehlung: 12 Monate in Git-Repo, danach archivieren.

### 11. Concept-Clarifier-Rolle
- Ist der Concept-Clarifier-Agent ueberfluessig, wenn Boris selbst die Vorgabe macht und kurz diskutiert?
- Empfehlung: Ersetzen durch ein lokales/einfaches Format-Template, kein eigener Agent noetig.

### 12. Budget-Cap pro Feature
- €5 pro Feature — reicht das bei Sonnet fuer alle Agenten-Schritte?
- Geschaetzte Kosten: €3-8 pro mittlerem Feature. Cap ggf. auf €8 erhoehen oder dynamisch nach Scope.
