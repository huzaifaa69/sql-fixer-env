from environment import SQLFixerEnv, SQLAction

SOLUTION_QUERIES = {
    "easy": "SELECT name, age FROM users WHERE age > 18",
    "medium": "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 100",
    "hard": "SELECT u.name, SUM(o.amount) as total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'completed' GROUP BY u.id, u.name ORDER BY total DESC LIMIT 3",
    "expert": "SELECT u.name, COUNT(o.id) as order_count FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name HAVING SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) = 0",
}

def grade_task(task_name: str) -> float:
    env = SQLFixerEnv(task_name)
    env.reset()
    action = SQLAction(query=SOLUTION_QUERIES[task_name])
    _, reward, _, _ = env.step(action)
    return reward

def run_all_graders():
    results = {}
    for task in ["easy", "medium", "hard", "expert"]:
        score = grade_task(task)
        results[task] = score
        print(f"Task: {task} | Score: {score}")
    return results

if __name__ == "__main__":
    run_all_graders()