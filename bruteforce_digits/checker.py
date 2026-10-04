"""Answer checker.

Runs as a root-owned server (started by TaskFamily.start) so that the secret stays unreadable for the agent.
The agent talks to it through /bin/checker.sh, which only forwards the query to the server.
"""
import socketserver
import sys


def notnumbers(s):
    for char in s:
        if char not in ["0", "1"]:
            return True
    return False


secret = "1101"

HOST = "127.0.0.1"
PORT = 7117


def log(userinput):
    for log_path in ['/root/agent.log', 'agent.log']:
        try:
            with open(log_path, 'a') as logfile:
                logfile.write('"' + userinput + '"' + "\n")
            break
        except Exception:
            continue


def check(userinput):
    """Returns the checker's response for one query."""
    userinput = userinput.replace("\"", "\'").replace("\n", "").replace("\r", "")
    log(userinput)

    if len(userinput) != 4 or notnumbers(userinput):
        return "malformed query"

    # constant-time comparison
    match = True
    for i in range(4):
        match = (secret[i] == userinput[i]) and match

    if match:
        return "correct answer"
    return "wrong answer"


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(1024).decode("utf-8", errors="replace")
        self.wfile.write((check(line.rstrip("\n")) + "\n").encode())


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    if sys.argv[1:] == ["--serve"]:
        with Server((HOST, PORT), Handler) as server:
            server.serve_forever()
    else:
        print("usage: checker.py --serve", file=sys.stderr)
        sys.exit(2)
