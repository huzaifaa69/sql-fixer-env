from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn
from environment import SQLFixerEnv, SQLAction

app = FastAPI(title="SQL Fixer OpenEnv")

# Global env instances for each task
envs = {
    "easy": SQLFixerEnv("easy"),
    "medium": SQLFixerEnv("medium"),
    "hard": SQLFixerEnv("hard")
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
            {"name": "easy", "difficulty": "easy"},
            {"name": "medium", "difficulty": "medium"},
            {"name": "hard", "difficulty": "hard"}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)