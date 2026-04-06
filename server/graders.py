from environment import SQLFixerEnv, SQLAction

def grade_task(task_name: str) -> float:
    """Run a task and return score 0.0-1.0"""
    env = SQLFixerEnv(task_name)
    solutions = {
        "easy": "SELECT name, age FROM users WHERE age > 18",
        "medium": "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 100",
        "hard": "SELECT u.name, SUM(o.amount) as total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'completed' GROUP BY u.id, u.name ORDER BY total DESC LIMIT 3"
    }
    env.reset()
    action = SQLAction(query=solutions[task_name])
    _, reward, _, _ = env.step(action)
    return reward

def run_all_graders():
    results = {}
    for task in ["easy", "medium", "hard"]:
        score = grade_task(task)
        results[task] = score
        print(f"Task: {task} | Score: {score}")
    return results

if __name__ == "__main__":
    run_all_graders()