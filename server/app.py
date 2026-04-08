from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn
from environment import SQLFixerEnv, SQLAction

app = FastAPI(title="SQL Fixer OpenEnv")

envs = {
    "easy": SQLFixerEnv("easy"),
    "medium": SQLFixerEnv("medium"),
    "hard": SQLFixerEnv("hard"),
    "expert": SQLFixerEnv("expert"),
}

class ResetRequest(BaseModel):
    task: Optional[str] = "easy"

class StepRequest(BaseModel):
    task: Optional[str] = "easy"
    query: str

@app.get("/")
def root():
    return {"status": "ok", "env": "sql-fixer"}

@app.post("/reset")
def reset(req: ResetRequest = ResetRequest()):
    task = req.task if req.task in envs else "easy"
    obs = envs[task].reset()
    return {"observation": obs.dict(), "task": task}

@app.post("/step")
def step(req: StepRequest):
    task = req.task if req.task in envs else "easy"
    action = SQLAction(query=req.query)
    obs, reward, done, info = envs[task].step(action)
    return {
        "observation": obs.dict(),
        "reward": reward,
        "done": done,
        "info": info
    }

@app.get("/state")
def state(task: str = "easy"):
    task = task if task in envs else "easy"
    return envs[task].state()

@app.get("/tasks")
def tasks():
    return {
        "tasks": [
            {"name": "easy", "difficulty": "easy", "description": "Fix syntax errors in a simple SELECT query"},
            {"name": "medium", "difficulty": "medium", "description": "Fix logic errors in a JOIN query"},
            {"name": "hard", "difficulty": "hard", "description": "Fix complex multi-table aggregation query"},
            {"name": "expert", "difficulty": "hard", "description": "Write query using HAVING and CASE expressions"},
        ]
    }

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()