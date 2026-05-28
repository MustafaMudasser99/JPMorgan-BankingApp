# JPMorgan Banking App

A full-stack banking application built with JPMorgan engineers as part of the Software Engineering in Industry programme at Bournemouth University. Developed over 10 weeks following Agile methodology with CI/CD, TDD, and security best practices.

---

## Tech Stack

- **Backend:** Django
- **Frontend:** HTML
- **Database:** SQLite
- **Containerisation:** Docker

---

## Features

- **Interest Calculator** — calculates interest based on account balance and rate
- **Savings Dashboard** — overview of savings progress and account activity
- **Round-Up Savings** — automatically rounds up transactions and moves the difference to savings
- **Night-Mode Savings** — API endpoint that requires additional authorisation for any request made between 12am and 6am, if enabled on the account. Designed to prevent late-night impulse spending

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) installed on your machine

### Running the App

```bash
git clone https://github.com/MustafaMudasser99/JPMorgan-BankingApp.git
cd JPMorgan-BankingApp
docker-compose up
```

The app will be available at `http://localhost:8000`

---

## Programme Context

Built as part of the **Software Engineering in Industry** programme at Bournemouth University, delivered by JPMorgan engineers. The programme covered Agile, CI/CD, TDD, BDD, containerisation, OSS vulnerability checks, and version control practices.
