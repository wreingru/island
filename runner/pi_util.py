"""Pi session recording helper (moved out of the v1 runner/run_race.py, which stays on main)."""
import json, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def record_pi(heats):
    node_bin = os.environ.get("NODE_BIN", "/workspace/island_swarm/tools/node-v22.20.0-linux-x64/bin/node")
    script = os.path.join(ROOT, "runner", "pi_record.mjs")
    import tempfile
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump({"root": ROOT, "heats": heats}, tf)
        out = subprocess.run([node_bin, script, tf.name], text=True,
                             capture_output=True, cwd=os.path.join(ROOT, "runner"), timeout=300)
        os.unlink(tf.name)
        if out.returncode != 0:
            raise RuntimeError(out.stderr[-500:])
        return json.loads(out.stdout)
    except Exception as e:
        print("Pi recording unavailable, using placeholders:", str(e)[:200], file=sys.stderr)
        return None
