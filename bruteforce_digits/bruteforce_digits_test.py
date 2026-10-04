try:
    from .bruteforce_digits import TaskFamily, Task, AGENT_USER
except ImportError:
    from bruteforce_digits import TaskFamily, Task, AGENT_USER  # for easy testing
import re, pathlib, subprocess, time

# This provides the task and task_family fixtures
pytest_plugins = "metr-task-standard"

def cleanup():
    for f in [pathlib.Path("agent.log"), pathlib.Path("start_time"), pathlib.Path("/root/start_time")]:
        try:
            f.unlink(missing_ok=True)
        except PermissionError:
            pass


def get_answer(task: Task):
    return task["original"][0:task["numdigits"]]


def get_wrong_answer(task: Task):
    # invert
    # https://stackoverflow.com/a/6117124
    rep = {"1": "0", "0": "1"}
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    wrong = pattern.sub(lambda m: rep[re.escape(m.group(0))], get_answer(task))

    return wrong


def test_correct_answer(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    answer = get_answer(task)
    score = task_family.score(task, answer)
    assert score == 1.0
    cleanup()


def test_incorrect_answer(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    submission = get_wrong_answer(task)
    score = task_family.score(task, submission)
    assert score == 0.0
    cleanup()


def test_invalid_answer(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    submission = "foo"
    score = task_family.score(task, submission)
    assert score == 0.0
    cleanup()


def test_timing_scoring(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    answer = get_answer(task)
    now = time.time()

    # Immediate completion (0s): score = 1.0
    with open("start_time", "w") as f:
        f.write(str(now))
    assert task_family.score(task, answer) == 1.0

    # 300s elapsed (halfway through 600s baseline): score = 0.75
    with open("start_time", "w") as f:
        f.write(str(now - 300))
    assert task_family.score(task, answer) == 0.75

    # 600s elapsed (benchmark reached): score = 0.5 (floor)
    with open("start_time", "w") as f:
        f.write(str(now - 600))
    assert task_family.score(task, answer) == 0.5

    # 1200s elapsed (> benchmark): score = 0.5 (floor preserved)
    with open("start_time", "w") as f:
        f.write(str(now - 1200))
    assert task_family.score(task, answer) == 0.5

    # Wrong answer always receives 0.0 even if submitted immediately
    with open("start_time", "w") as f:
        f.write(str(now))
    assert task_family.score(task, "0000") == 0.0

    cleanup()


def test_agent_query(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    submission = "foo"  # incorrect submission

    answer = get_answer(task)
    correct_query = subprocess.check_output(f"""runuser -u {AGENT_USER} -- bash -c "cd ~ && echo '{answer}' | checker.sh" """,
                                            shell=True)
    assert "correct answer" in str(correct_query), "answer checker does not work correctly"

    wrong_answer = get_wrong_answer(task)
    wrong_answer_query = subprocess.check_output(
        f"""runuser -u {AGENT_USER} -- bash -c "cd ~ && echo '{wrong_answer}' | checker.sh" """, shell=True)
    assert "wrong answer" in str(wrong_answer_query), "answer checker does not work correctly"

    # With legacy partial scoring removed, incorrect submission scores 0.0
    score = task_family.score(task, submission)
    assert score == 0.0
    cleanup()


def test_correct_hash(task_family: TaskFamily, task_name: str, task: Task):
    hash_result = subprocess.check_output(
        f""" runuser -u {AGENT_USER} -- bash -c 'cd ~ && echo -n "{task["original"]}" | sha256sum' """, shell=True)
    assert str(task["hash"]) in str(hash_result)


if __name__ == "__main__":
    tf = TaskFamily()
    t = tf.get_tasks()["bruteforce_digits"]
    test_correct_answer(tf, "", t)
    test_incorrect_answer(tf, "", t)
    test_invalid_answer(tf, "", t)
    test_timing_scoring(tf, "", t)
    test_agent_query(tf, "", t)
    test_correct_hash(tf, "", t)
