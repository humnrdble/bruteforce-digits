try:
    from .bruteforce_digits import TaskFamily, Task, AGENT_USER
except ImportError:
    from bruteforce_digits import TaskFamily, Task, AGENT_USER  # for easy testing
import re, pathlib, subprocess

# This provides the task and task_family fixtures
pytest_plugins = "metr-task-standard"

def cleanup():
    file_to_remove = pathlib.Path("agent.log")
    file_to_remove.unlink(missing_ok=True)


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
    # If your task requires any setup, first check that it's been performed correctly,
    # e.g. assert that necessary files exist and software is installed.

    # Before submitting an answer, you can perform any actions inside the task container,
    # e.g. modify files or SSH into an aux VM and run a program there.
    cleanup()
    answer = get_answer(task)
    score = task_family.score(task, answer)
    assert score == 1
    cleanup()

def test_incorrect_answer(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    submission = get_wrong_answer(task)
    score = task_family.score(task, submission)
    assert score == 0
    cleanup()


def test_invalid_answer(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    submission = "foo"
    score = task_family.score(task, submission)
    assert score == 0
    cleanup()


def test_agent_query(task_family: TaskFamily, task_name: str, task: Task):
    cleanup()
    submission = "foo"  # incorrect submission

    answer = get_answer(task)
    correct_query = subprocess.check_output(f"""sudo -u {AGENT_USER} bash -c "echo '{answer}' | checker.sh" """,
                                            shell=True)
    assert "correct answer" in str(correct_query), "answer checker does not work correctly"

    wrong_answer = get_wrong_answer(task)
    wrong_answer_query = subprocess.check_output(
        f"""sudo -u {AGENT_USER} bash -c "echo '{wrong_answer}' | checker.sh" """, shell=True)
    assert "wrong answer" in str(wrong_answer_query), "answer checker does not work correctly"

    score = task_family.score(task, submission)
    assert score == 0.9
    cleanup()


def test_correct_hash(task_family: TaskFamily, task_name: str, task: Task):
    hash_result = subprocess.check_output(
        f""" sudo -u {AGENT_USER} bash -c 'echo -n "{task["original"]}" | sha256sum' """, shell=True)
    assert str(task["hash"]) in str(hash_result)


if __name__ == "__main__":
    tf = TaskFamily()
    test_correct_answer(tf, "", tf.get_tasks()["bruteforce-digits"])
    test_incorrect_answer(tf, "", tf.get_tasks()["bruteforce-digits"])
    test_invalid_answer(tf, "", tf.get_tasks()["bruteforce-digits"])
    test_agent_query(tf, "", tf.get_tasks()["bruteforce-digits"])
    test_correct_hash(tf, "", tf.get_tasks()["bruteforce-digits"])
