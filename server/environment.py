import sqlite3
import re
from typing import Optional
from pydantic import BaseModel

class SQLAction(BaseModel):
    query: str

class SQLObservation(BaseModel):
    task_description: str
    broken_query: str
    schema_info: str
    last_result: Optional[str] = None
    last_error: Optional[str] = None
    hint: Optional[str] = None
    step: int = 0

class SQLReward(BaseModel):
    value: float
    reason: str

TASKS = {
    "easy": {
        "description": "Fix the syntax error in this SQL query. The query should return names and ages of users older than 18.",
        "broken": "SELEC name, age FORM users WERE age > 18",
        "solution": "SELECT name, age FROM users WHERE age > 18",
        "hint": "Check for typos in SQL keywords: SELEC, FORM, WERE",
        "schema": "Table: users(id INTEGER, name TEXT, age INTEGER)\nTable: orders(id INTEGER, user_id INTEGER, amount REAL, status TEXT)",
        "expected_rows": [("Alice", 25), ("Carol", 30), ("Dave", 22)],
        "expected_columns": ["name", "age"],
    },
    "medium": {
        "description": "Fix the logic error. The query should return names of users who have orders with amount greater than 100.",
        "broken": "SELECT u.name FROM users u JOIN orders o ON u.id = o.id WHERE o.amount < 100",
        "solution": "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 100",
        "hint": "Check both the JOIN condition (o.id vs o.user_id) and the WHERE comparison direction (< vs >)",
        "schema": "Table: users(id INTEGER, name TEXT, age INTEGER)\nTable: orders(id INTEGER, user_id INTEGER, amount REAL, status TEXT)",
        "expected_rows": [("Alice",), ("Bob",), ("Dave",)],
        "expected_columns": ["name"],
    },
    "hard": {
        "description": "Fix this query to find top 3 customers by total spending on completed orders only, showing name and total amount, ordered from highest to lowest.",
        "broken": "SELECT u.name, SUM(o.amount) FROM users u, orders o WHERE o.status = 'completed' GROUP BY u.name ORDER BY SUM(o.amount) LIMIT 3",
        "solution": "SELECT u.name, SUM(o.amount) as total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'completed' GROUP BY u.id, u.name ORDER BY total DESC LIMIT 3",
        "hint": "Fix: (1) use explicit JOIN with correct key, (2) add DESC to ORDER BY, (3) GROUP BY should include u.id",
        "schema": "Table: users(id INTEGER, name TEXT, age INTEGER)\nTable: orders(id INTEGER, user_id INTEGER, amount REAL, status TEXT)",
        "expected_rows": [("Dave", 300.0), ("Alice", 150.0), ("Carol", 50.0)],
        "expected_columns": ["name", "total"],
    },
    "expert": {
        "description": "Write a query to find users who have ONLY cancelled orders (no completed orders at all), showing their name and total number of orders.",
        "broken": "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'cancelled'",
        "solution": "SELECT u.name, COUNT(o.id) as order_count FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name HAVING SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) = 0",
        "hint": "You need HAVING clause to filter groups, and a CASE expression to check for absence of completed orders",
        "schema": "Table: users(id INTEGER, name TEXT, age INTEGER)\nTable: orders(id INTEGER, user_id INTEGER, amount REAL, status TEXT)",
        "expected_rows": [("Bob", 1)],
        "expected_columns": ["name", "order_count"],
    },
}

class SQLFixerEnv:
    def __init__(self, task: str = "easy"):
        self.task_name = task
        self.task = TASKS[task]
        self.steps = 0
        self.max_steps = 5
        self.solved = False
        self.best_score = 0.01
        self.db = self._setup_db()

    def _setup_db(self):
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
        cur.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL, status TEXT)")
        cur.executemany("INSERT INTO users VALUES (?,?,?)", [
            (1, "Alice", 25), (2, "Bob", 17), (3, "Carol", 30), (4, "Dave", 22)
        ])
        cur.executemany("INSERT INTO orders VALUES (?,?,?,?)", [
            (1, 1, 150.0, "completed"),
            (2, 1, 80.0, "cancelled"),
            (3, 2, 200.0, "cancelled"),
            (4, 3, 50.0, "completed"),
            (5, 4, 300.0, "completed"),
        ])
        conn.commit()
        return conn

    def reset(self):
        self.steps = 0
        self.solved = False
        self.best_score = 0.01
        self.db = self._setup_db()
        return SQLObservation(
            task_description=self.task["description"],
            broken_query=self.task["broken"],
            schema_info=self.task["schema"],
            hint=self.task["hint"],
            step=0
        )

    def step(self, action: SQLAction):
        self.steps += 1
        query = action.query.strip()
        done = False
        error = None
        result = None

        try:
            cur = self.db.cursor()
            cur.execute(query)
            result = str(cur.fetchall())
        except Exception as e:
            error = str(e)

        reward = self._grade(query, error)
        self.best_score = max(self.best_score, reward)

        if reward >= 0.95:
            self.solved = True
            done = True
        elif self.steps >= self.max_steps:
            done = True

        obs = SQLObservation(
            task_description=self.task["description"],
            broken_query=self.task["broken"],
            schema_info=self.task["schema"],
            last_result=result,
            last_error=error,
            step=self.steps
        )
        return obs, reward, done, {"steps": self.steps, "best_score": self.best_score}

    def _grade(self, query: str, error: Optional[str]) -> float:
        score = 0.0
        query_up = query.upper().strip()
        solution_up = self.task["solution"].upper()

        # 1. Syntax check (can it run at all?) — 20%
        if not error:
            score += 0.20

        # 2. Keyword matching — 25%
        keywords = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "ORDER BY", "LIMIT", "HAVING", "ON"]
        solution_keywords = [k for k in keywords if k in solution_up]
        if solution_keywords:
            matched = sum(1 for k in solution_keywords if k in query_up)
            score += 0.25 * (matched / len(solution_keywords))

        # 3. Correct tables referenced — 20%
        solution_tables = set(re.findall(r'(?:FROM|JOIN)\s+(\w+)', solution_up))
        query_tables = set(re.findall(r'(?:FROM|JOIN)\s+(\w+)', query_up))
        if solution_tables:
            table_score = len(solution_tables & query_tables) / len(solution_tables)
            score += 0.20 * table_score

        # 4. Correct JOIN condition — 15%
        if "JOIN" in solution_up:
            if "USER_ID" in query_up and "JOIN" in query_up:
                score += 0.15
            elif "JOIN" in query_up:
                score += 0.05

        # 5. Result correctness — 20%
        if not error:
            try:
                cur = self.db.cursor()
                cur.execute(query)
                actual_rows = cur.fetchall()
                expected_rows = self.task["expected_rows"]
                if set(actual_rows) == set(expected_rows):
                    score += 0.20
                elif len(actual_rows) == len(expected_rows):
                    score += 0.10
                elif len(actual_rows) > 0:
                    score += 0.05
            except:
                pass

        # Clamp strictly between 0 and 1
        score = round(score, 3)
        score = max(0.01, min(0.99, score))
        return score

    def state(self):
        return {
            "task": self.task_name,
            "steps": self.steps,
            "max_steps": self.max_steps,
            "solved": self.solved,
            "best_score": self.best_score
        }