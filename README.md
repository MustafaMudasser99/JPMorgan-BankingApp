# JPMorgan Banking App

A production-grade Django REST banking platform built with JPMorgan engineers as part of the **Software Engineering in Industry** programme at Bournemouth University. Developed over 10 weeks following Agile methodology, with CI/CD automation, TDD, BDD, and security-first engineering practices applied throughout.

> **Live programme context:** This was not a tutorial project. It was delivered under the direct mentorship of JPMorgan software engineers, adhering to the engineering standards expected in a regulated financial institution.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django (REST APIs) |
| Frontend | HTML, CSS |
| Database | SQLite |
| Containerisation | Docker + docker-compose |
| CI/CD | Jenkins (5-stage pipeline) |
| Version Control | Git / GitHub |

---

## CI/CD Pipeline

The application is automated via a **5-stage Jenkins pipeline** defined in [`Jenkinsfile`](./Jenkinsfile):

```
Checkout → Python Environment Setup → Dependency Installation → Django Migrations → Automated Test Execution
```

**Post-build actions:**
- Artefact archiving (static files)
- Failure notifications with log references

This pipeline enforces that no code reaches deployment without passing the full automated test suite — consistent with quality-gate practices in production banking environments.

---

## Docker Setup

The application is fully containerised using Docker and orchestrated with `docker-compose`.

```bash
git clone https://github.com/MustafaMudasser99/JPMorgan-BankingApp.git
cd JPMorgan-BankingApp
docker-compose up
```

Access the app at `http://localhost:8000`

---

## Features

### Interest Calculator
Calculates projected interest based on current account balance and applicable rate. Designed for clarity and accuracy in savings planning.

### Savings Dashboard
Overview of savings progress and account activity. Surfaces key metrics at a glance to help users track financial goals.

### Round-Up Savings
Automatically rounds up transactions to the nearest pound and transfers the difference to a savings pot — a behavioural nudge feature common in modern fintech products (Monzo, Starling).

### Night-Mode Savings ⭐
A **security-focused API endpoint** that applies time-based authorisation logic to restrict all transactions between **12am–6am** if the feature is enabled on the account.

- Requires additional authorisation for any request in the restricted window
- Designed to prevent late-night impulse spending
- Demonstrates security-first API design: access control embedded at the business logic layer, not just the infrastructure layer

```python
# Simplified logic
if night_mode_enabled and current_hour in range(0, 6):
    raise PermissionDenied("Transactions restricted. Night-Mode Savings is active.")
```

---

## Engineering Practices

This project was built following the full engineering discipline expected in a financial services environment:

- **TDD** — test suite written alongside feature development, executed automatically on every commit via Jenkins
- **BDD** — behaviour-driven scenarios used to define acceptance criteria before implementation
- **OSS vulnerability checks** — open-source dependency scanning applied to `requirements.txt`
- **Agile methodology** — two-week sprint cadence, daily stand-ups, retrospectives with JPMorgan engineers
- **Code review** — all contributions reviewed by peers and programme mentors before merging

---

## My Contributions

| Feature | Description |
|---|---|
| Dashboard | Main account overview and activity feed |
| Interest Calculator | Balance × rate calculation with UI |
| Savings Dashboard | Progress tracking and account summary |
| Round-Up Savings | Transaction rounding and auto-transfer logic |
| Night-Mode Savings API | Time-gated authorisation endpoint (12am–6am) |
| Jenkins CI/CD Pipeline | Full 5-stage pipeline with test automation and artefact archiving |
| Docker Setup | Containerisation and docker-compose orchestration |

---

## Programme Context

**Software Engineering in Industry** — Bournemouth University × JPMorgan Chase

A 10-week structured programme delivering real-world software engineering experience under the mentorship of practising JPMorgan engineers. Curriculum covered:

- Agile / Scrum methodology
- CI/CD pipeline design and implementation
- Test-driven development (TDD) and behaviour-driven development (BDD)
- Containerisation with Docker
- OSS vulnerability scanning
- Version control and collaborative Git workflows
- Security practices in financial software development

---

## Author

**Mustafa Mudasser**  
Python Engineer | Applied AI | Fintech  
[LinkedIn](https://www.linkedin.com/in/mustafa-mudasser) · [GitHub](https://github.com/MustafaMudasser99) · [Portfolio](https://portfolio-liart-chi-16.vercel.app/)
