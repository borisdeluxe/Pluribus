# Tech Debt

Bewusst aufgeschobene Implementierungen. Jeder Eintrag hat Kontext, Trigger und geschätzten Aufwand.

---

## TD-001: Security-Checklist Skill mit Scanner-Integration

**Status:** Offen
**Erstellt:** 2026-04-24
**Ziel-Phase:** Phase 1 (Server-Setup)

### Kontext

Der aktuelle `security-checklist` Skill ist rein LLM-basiert. Das führt zu:
- Halluzinations-Risiko bei Findings
- Keine deterministische Baseline
- Keine Reproduzierbarkeit (keine Version-Pinning)
- Kein automatisches CWE/OWASP-Mapping

### Ziel-Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Agent Policy                                           │
│ Prompt-Template mit expliziter Versions-Referenz                │
│ "Du prüfst gegen OWASP Top 10:2025, ASVS 5.0.0 Level L2..."    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Version-Pinning + Update-Prozess                       │
│ Monatlicher Cronjob: GitHub API/RSS → Re-Index Vektor-DB        │
│ Quellen: OWASP/ASVS, OWASP/Top10, genai.owasp.org, MITRE CWE   │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: RAG-Knowledgebase                                      │
│ Vektor-DB mit: ASVS 5.0 CSV, OWASP Cheat Sheets,               │
│ LLM Top 10, Agentic Top 10, CWE Top 25                         │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Statische Scanner (Ground Truth)                       │
│ Semgrep + Trivy + Gitleaks                                      │
│ Output: SARIF → automatisches CWE/OWASP-Mapping                 │
└─────────────────────────────────────────────────────────────────┘
```

### Trigger

- Server-Setup (CAX31) abgeschlossen
- Scanner installiert und lauffähig

### Aufwand

- Scanner-Installation: 2h
- RAG-Setup (Vektor-DB + Indexing): 4h
- Skill-Überarbeitung: 2h
- Update-Cronjob: 2h
- **Gesamt: ~10h**

### Referenzen

- `references/security-standards.yaml` — Vollständige Standards-Liste
- `.claude/skills/security-checklist/SKILL.md` — Aktueller Skill (zu überarbeiten)

---

## TD-002: Spec-Review Findings umsetzen

**Status:** Offen
**Erstellt:** 2026-04-24
**Ziel-Phase:** Vor TK14 v1 Finalisierung

### Kontext

Spec-Review (OpenAI + Gemini) hat 14 Punkte identifiziert. 6 HIGH-Priorität.

### HIGH-Priorität (muss vor v1)

| # | Änderung | Beschreibung |
|---|----------|--------------|
| 1 | Persistente Task-Queue | LISTEN/NOTIFY nur als Wake-Up, nicht als Datentransport |
| 2 | Server-side Hard Constraint Protection | GitHub Action statt pre-commit Hook |
| 3 | Graceful Shutdown bei hard_stop | Agents clean terminieren, nicht killen |
| 4 | Backup-Admin-Rolle | Zweite Person neben Boris mit Override-Rechten |
| 5 | Atomic Budget Updates | `UPDATE ... SET cost = cost + ?` statt read-then-write |
| 6 | git diff Check nach Implementer | Technische Enforcement für TDD, nicht nur Prompt |

### MEDIUM-Priorität (kann Phase 1)

| # | Änderung |
|---|----------|
| 7 | Anomaly Detector Warm-Up (min 20 Features) |
| 8 | Kanonisches State-Diagramm hinzufügen |
| 9 | User-Separation für Orchestrator/Observers |
| 10 | /agency cancel Slash-Command |
| 11 | Fast-Lane LOC-Berechnung durch Orchestrator |
| 12 | forbidden_paths Syntax bereinigen |

### Trigger

- TK14 v1 Ausarbeitung beginnt

### Referenzen

- Spec-Review Output in dieser Conversation (2026-04-24)

---

## TD-003: Remaining Skills mit Scanner-Output integrieren

**Status:** Offen
**Erstellt:** 2026-04-24
**Ziel-Phase:** Phase 2

### Kontext

Wenn TD-001 (Scanner-Integration) abgeschlossen ist, sollten auch andere Skills die Scanner-Outputs nutzen können:
- `code-review` Skill: Trivy für Dependency-Check, Semgrep für Code-Patterns
- `tdd-red-green` Skill: Coverage-Reports als strukturierter Input

### Trigger

- TD-001 abgeschlossen

### Aufwand

- ~4h pro Skill

---

## TD-004: Generalisierung für Multi-Projekt-Einsatz

**Status:** Offen
**Erstellt:** 2026-04-25
**Ziel-Phase:** Nach Falara-Produktivbetrieb

### Kontext

Mutirada ist aktuell auf Falara zugeschnitten:
- `docs-update` Skill referenziert `falara-api-docs` Repo und `/v1/*` Endpoints
- TK14 enthält Falara-spezifische Server-IPs, Domains
- Keine Config-Datei für Projekt-Parameter

### Ziel

```yaml
# /opt/agency/config.yaml
project:
  name: "projekt-name"
  repo: "github.com/user/repo"
  docs_repo: "github.com/user/docs"  # optional

endpoints:
  public: ["/api/*"]
  internal: ["/admin/*", "/internal/*"]

budget:
  per_feature_eur: 5.00
  per_day_eur: 20.00
  per_week_eur: 100.00
```

### Änderungen

1. Config-Loader für `config.yaml`
2. Skills lesen Projekt-Config statt Hardcodes
3. TK14 Template ohne projekt-spezifische Werte
4. Docs: "Getting Started für neues Projekt"

### Trigger

- Falara läuft stabil (2-4 Wochen Produktivbetrieb)
- Bedarf für zweites Projekt

### Aufwand

- Config-System: 2h
- Skills anpassen: 2h
- Docs: 1h
- **Gesamt: ~5h**

---

## Format für neue Einträge

```markdown
## TD-XXX: [Titel]

**Status:** Offen | In Arbeit | Erledigt
**Erstellt:** YYYY-MM-DD
**Ziel-Phase:** Phase X

### Kontext
[Warum wurde das aufgeschoben?]

### Trigger
[Wann soll das angegangen werden?]

### Aufwand
[Geschätzte Zeit]

### Referenzen
[Relevante Dokumente/Dateien]
```
