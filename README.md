# SQL Fixer Environment

An OpenEnv environment where an AI agent must identify and fix broken SQL queries of varying complexity.

## Environment Description

The agent receives a broken SQL query and must fix it. The environment uses an in-memory SQLite database with realistic tables (users, orders). Rewards are based on partial progress — keyword correctness, table references, and query executability.

## Action Space
```json
{
  "query": "string — the fixed SQL query"
}
```

## Observation Space
```json
{
  "task_description": "string",
  "broken_query": "string",
  "schema_info": "string",
  "last_result": "string or null",
  "last_error": "string or null",
  "hint": "string or null"
}
```

## Tasks

| Task | Difficulty | Description | Expected Score |
|------|-----------|-------------|----------------|
| easy | Easy | Fix syntax errors in a simple SELECT query | 0.9+ |
| medium | Medium | Fix logic errors in a JOIN query | 0.7+ |
| hard | Hard | Fix complex multi-table aggregation query | 0.5+ |

## Setup Instructions
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
cd server
python app.py

# Run inference
python inference.py
```

## Docker
```bash
docker build -t sql-fixer-env .
docker run -p 7860:7860 sql-fixer-env
```

## Baseline Scores

| Task | Baseline Score |
|------|---------------|
| easy | 0.90 |
| medium | 0.70 |
| hard | 0.50 |