"""Stand-in for the `claude` CLI in tests: replays a recorded stream-json file.

Environment:
  FAKE_CLAUDE_STREAM  JSONL file to print ("/PROJECT" is replaced by the working directory)
  FAKE_CLAUDE_DELAY   seconds to sleep between lines (default 0)
  FAKE_CLAUDE_RECORD  file to append {"argv", "stdin", "cwd", "child_pid"} to, one JSON per call
  FAKE_CLAUDE_EXIT    exit code (default 0)
  FAKE_CLAUDE_STDERR  text written to stderr
  FAKE_CLAUDE_CHILD   if "1", start a long `sleep` child (to check process-group stop)
"""
import json
import os
import subprocess
import sys
import time

stdin = sys.stdin.read()
child = subprocess.Popen(["sleep", "30"]) if os.environ.get("FAKE_CLAUDE_CHILD") == "1" else None
record = os.environ.get("FAKE_CLAUDE_RECORD")
if record:
    with open(record, "a") as f:
        f.write(json.dumps({"argv": sys.argv[1:], "stdin": stdin, "cwd": os.getcwd(),
                            "child_pid": child.pid if child else None}) + "\n")

if os.environ.get("FAKE_CLAUDE_STDERR"):
    sys.stderr.write(os.environ["FAKE_CLAUDE_STDERR"])
    sys.stderr.flush()

delay = float(os.environ.get("FAKE_CLAUDE_DELAY") or 0)
stream = os.environ.get("FAKE_CLAUDE_STREAM")
if stream:
    with open(stream) as f:
        for line in f:
            sys.stdout.write(line.replace("/PROJECT", os.getcwd()))
            sys.stdout.flush()
            if delay:
                time.sleep(delay)

sys.exit(int(os.environ.get("FAKE_CLAUDE_EXIT") or 0))
