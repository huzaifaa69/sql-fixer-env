import sqlite3
import re
from typing import Optional
from pydantic import BaseModel

# --- Models ---
class SQLAction(BaseModel):
    query: str

class SQLObservation(BaseModel):
    task_description: str
    broken_query: str
    schema_info: str
    last_result: Optional[str] = None
    last_error: Optional[str] = None
    hint: Optional[str] = None

class SQLReward(BaseModel):
    value: float
    reason: str

# --- Tasks ---
TASKS = {
    "easy": {
        "description": "Fix the syntax error in this SQL query",
        "broken": "SELEC name, age FORM users WERE age > 18",
        "solution": "SELECT name, age FROM users WHERE age > 18",
        "hint": "Check for typos in SQL keywords",
        "schema": "Table: users(id INTEGER, name TEXT, age INTEGER)",
    },
    "medium": {
        "description": "Fix the logic error - query should return users with orders over $100",
        "broken": "SELECT u.name FROM users u JOIN orders o ON u.id = o.id WHERE o.amount < 100",
        "solution": "SELECT u.name FROM users u JOIN orders o ON u.user_id = o.user_id WHERE o.amount > 100",
        "hint": "Check the JOIN condition and WHERE clause direction",
        "schema": "Table: users(id INTEGER, name TEXT), Table: orders(id INTEGER, user_id INTEGER, amount REAL)",
    },
    "hard": {
        "description": "Fix this query to find top 3 customers by total spending, excluding cancelled orders",
        "broken": "SELECT u.name, SUM(o.amount) FROM users u, orders o WHERE o.status = 'completed' GROUP BY u.name ORDER BY SUM(o.amount) LIMIT 3",
        "solution": "SELECT u.name, SUM(o.amount) as total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'completed' GROUP BY u.id, u.name ORDER BY total DESC LIMIT 3",
        "hint": "Fix the JOIN, add proper aliasing, and check ORDER BY direction",
        "schema": "Table: users(id INTEGER, name TEXT), Table: orders(id INTEGER, user_id INTEGER, amount REAL, status TEXT)",
    }
}

class SQLFixerEnv:
    def __init__(self, task: str = "easy"):
        self.task_name = task
        self.task = TASKS[task]
        self.steps = 0
        self.max_steps = 5
        self.solved = False
        self.db = self._setup_db()

    def _setup_db(self):
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
        cur.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL, status TEXT)")
        cur.executemany("INSERT INTO users VALUES (?,?,?)", [
            (1,"Alice",25),(2,"Bob",17),(3,"Carol",30),(4,"Dave",22)
        ])
        cur.executemany("INSERT INTO orders VALUES (?,?,?,?)", [
            (1,1,150.0,"completed"),(2,1,80.0,"cancelled"),
            (3,2,200.0,"completed"),(4,3,50.0,"completed"),
            (5,4,300.0,"completed")
        ])
        conn.commit()
        return conn

    def reset(self):
        self.steps = 0
        self.solved = False
        self.db = self._setup_db()
        return SQLObservation(
            task_description=self.task["description"],
            broken_query=self.task["broken"],
            schema_info=self.task["schema"],
            hint=self.task["hint"]
        )

    def step(self, action: SQLAction):
        self.steps += 1
        query = action.query.strip()
        reward = 0.0
        done = False
        error = None
        result = None

        # Try running the query
        try:
            cur = self.db.cursor()
            cur.execute(query)
            result = str(cur.fetchall())
        except Exception as e:
            error = str(e)

        # Score the query
        reward = self._grade(query, error)

        if reward >= 0.9:
            self.solved = True
            done = True
        elif self.steps >= self.max_steps:
            done = True

        obs = SQLObservation(
            task_description=self.task["description"],
            broken_query=self.task["broken"],
            schema_info=self.task["schema"],
            last_result=result,
            last_error=error
        )
        return obs, reward, done, {"steps": self.steps}

    def _grade(self, query: str, error: Optional[str]) -> float:
        if error:
            return 0.01
        solution = self.task["solution"].upper()
        query_up = query.upper()
        score = 0.0
        keywords = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "ORDER BY", "LIMIT"]
        solution_keywords = [k for k in keywords if k in solution]
        matched = sum(1 for k in solution_keywords if k in query_up)
        score += 0.5 * (matched / len(solution_keywords)) if solution_keywords else 0
        solution_tables = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', solution)
        query_tables = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', query_up)
        solution_tables_flat = [t for pair in solution_tables for t in pair if t]
        query_tables_flat = [t for pair in query_tables for t in pair if t]
        if solution_tables_flat:
            table_score = sum(1 for t in solution_tables_flat if t in query_tables_flat) / len(solution_tables_flat)
            score += 0.3 * table_score
        if not error and len(query) > 10:
            score += 0.2
            score = min(round(score, 2), 0.99)
            score = max(score, 0.01)
            return score

    def state(self):
        return {
            "task": self.task_name,
            "steps": self.steps,
            "max_steps": self.max_steps,
            "solved": self.solved
        }