"""Agent for evals/run.sh, passed to inspect as --solver (replaces the bridge's default agent).

Same loop as the bridge's default (inspect's basic_agent with bash and python tools, run as the `agent` user, 120 s
timeout), with two differences:
- timeouts are not retried: inspect's docker exec reruns a timed-out command with 60 s and 30 s timeouts, so a
  timed-out call took ~216 s and ran the command up to three times. Here a call returns after TIMEOUT seconds and
  the command runs once. (An aborted command is not killed in the container; it keeps running.)
- the tool descriptions tell the model about the timeout and how to run longer jobs.
"""

from inspect_ai.solver import Solver, basic_agent, solver
from inspect_ai.tool import Tool, tool
from inspect_ai.util import sandbox

TIMEOUT = 120
AGENT_USER = "agent"

TIMEOUT_NOTE = (
    f"If a call is still running after {TIMEOUT} seconds it returns only a timeout error, with no output "
    "(the command itself keeps running). For anything longer, start it detached, "
    "e.g. `nohup mycommand > out.log 2>&1 &`, and read `out.log` in later calls."
)


def _output(result) -> str:
    return f"{result.stderr}\n{result.stdout}" if result.stderr else result.stdout


@tool
def bash() -> Tool:
    async def execute(cmd: str) -> str:
        """
        Use this function to execute bash commands. TIMEOUT_NOTE

        Args:
          cmd (str): The bash command to execute.

        Returns:
          The output of the command.
        """
        result = await sandbox().exec(
            cmd=["bash", "--login", "-c", cmd], timeout=TIMEOUT, timeout_retry=False, user=AGENT_USER
        )
        return _output(result)

    execute.__doc__ = execute.__doc__.replace("TIMEOUT_NOTE", TIMEOUT_NOTE)
    return execute


@tool
def python() -> Tool:
    async def execute(code: str) -> str:
        """
        Use the python function to execute Python code. TIMEOUT_NOTE

        The Python tool executes single-run Python scripts. Important notes:
        1. Each execution is independent - no state is preserved between runs
        2. You must explicitly use print() statements to see any output
        3. Simply writing expressions (like in notebooks) will not display results
        4. The script cannot accept interactive input during execution
        5. Return statements alone won't produce visible output
        6. All variables and imports are cleared between executions
        7. Standard output (via print()) is the only way to see results

        Args:
          code (str): The python code to execute.

        Returns:
          The output of the Python code.
        """
        result = await sandbox().exec(
            cmd=["bash", "--login", "-c", "python3 -"],
            input=code,
            timeout=TIMEOUT,
            timeout_retry=False,
            user=AGENT_USER,
        )
        return _output(result)

    execute.__doc__ = execute.__doc__.replace("TIMEOUT_NOTE", TIMEOUT_NOTE)
    return execute


@solver
def agent() -> Solver:
    return basic_agent(tools=[bash(), python()])
