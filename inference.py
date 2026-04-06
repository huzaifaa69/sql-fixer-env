import asyncio
import os
import textwrap
from typing import List, Optional
from openai import OpenAI
import httpx

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
TASK_NAME = os.getenv("SQL_ENV_TASK", "easy")
BENCHMARK = "sql-fixer-env"
ENV_URL = os.getenv("ENV_URL") or "http://localhost:7860"
MAX_STEPS = 5

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)

def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def get_fix(client, broken_query, schema, last_error, step):
    prompt = textwrap.dedent(f"""
    You are a SQL expert. Fix the broken SQL query below.
    
    Schema: {schema}
    Broken query: {broken_query}
    Previous error: {last_error or 'None'}
    Step: {step}
    
    Reply with ONLY the fixed SQL query, nothing else.
    """).strip()
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as e:
        return "SELECT 1"

def run_task(task_name):
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    rewards = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset
        r = httpx.post(f"{ENV_URL}/reset", json={"task": task_name}, timeout=30)
        data = r.json()
        obs = data["observation"]
        broken_query = obs["broken_query"]
        schema = obs["schema_info"]
        last_error = None

        for step in range(1, MAX_STEPS + 1):
            fixed_query = get_fix(client, broken_query, schema, last_error, step)
            
            r = httpx.post(f"{ENV_URL}/step", json={"task": task_name, "query": fixed_query}, timeout=30)
            result = r.json()
            
            reward = result["reward"]
            done = result["done"]
            last_error = result["observation"].get("last_error")
            
            rewards.append(reward)
            steps_taken = step
            
            log_step(step=step, action=fixed_query, reward=reward, done=done, error=last_error)
            
            if done:
                break

        score = max(rewards) if rewards else 0.0
        success = score >= 0.8

    except Exception as e:
        print(f"[DEBUG] Error: {e}", flush=True)
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score

def main():
    tasks = ["easy", "medium", "hard"]
    for task in tasks:
        run_task(task)

if __name__ == "__main__":
    main()