#!/usr/bin/env python3
"""Work through a folder of trial tasks: ask the local model, then score.

    python tools/trials/run_queue.py TASK_DIR [--n 8] [--rounds 1] [--no-model]

For every TASK_DIR/*.json without a matching *.result.json:
  1. unless --no-model, ask the local model (llm_candidates.py) for --n
     candidates, --rounds times;
  2. score all candidates (variant_trial.py) and write *.result.json.

Results are written next to the tasks, so the folder can live in the
agent-mailbox repo and be pushed back for review. Safe to stop and restart:
finished tasks are skipped.
"""

import argparse
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--no-model", action="store_true")
    ap.add_argument("--model")
    args = ap.parse_args()

    tasks = sorted(p for p in glob.glob(os.path.join(args.task_dir, "*.json"))
                   if not p.endswith(".result.json"))
    for task in tasks:
        result = os.path.splitext(task)[0] + ".result.json"
        if os.path.exists(result):
            continue
        print(f"== {os.path.basename(task)}", flush=True)
        if not args.no_model:
            for _ in range(args.rounds):
                cmd = [sys.executable, os.path.join(HERE, "llm_candidates.py"), task, "--n", str(args.n)]
                if args.model:
                    cmd += ["--model", args.model]
                subprocess.run(cmd)
        subprocess.run([sys.executable, os.path.join(HERE, "variant_trial.py"), task, "--out", result])


if __name__ == "__main__":
    main()
