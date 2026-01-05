# Swerve Telemetry Simulator

A Python-based simulator that generates realistic swerve-drive telemetry and
stores it in MySQL for structured analysis using SQL.

This project models per-module angle, RPM, current, and temperature data,
supports run-based isolation, and provides analytical SQL queries for
block-based performance metrics.

---

## Features

- Simulated 4-module swerve drive telemetry
- Per-tick telemetry logging (angle, RPM, current, temperature)
- Battery voltage sag modeling
- Millisecond-accurate elapsed time tracking
- Run isolation using `run_id`
- MySQL schema with optimized indexes
- Analytical SQL queries (per-module + per-block statistics)

---

## Tech Stack

- **Python 3**
- **MySQL 8+**
- **SQL**
- **DataGrip** (for querying / visualization)

---

## Repository Structure
``` text
├─ python/
│ └─ sim.py # Telemetry simulation + DB ingestion
│
├─ sql/
│ ├─ schema.sql # Database + tables + indexes
│ ├─ queries.sql # Analytics queries
│ └─ teardown.sql # Optional DB reset
│
├─ .gitignore
├─ README.md
└─ requirements.txt
```
---

## Setup Instructions

### 1) Create the database schema
Run the schema file in MySQL or DataGrip:

```sql
SOURCE sql/schema.sql;
