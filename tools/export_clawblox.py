#!/usr/bin/env python3
"""Inject course.json into clawblox/main.lua (between the COURSE JSON markers)."""
import json, os, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
course = json.load(open(os.path.join(ROOT, "course.json")))
lua_path = os.path.join(ROOT, "clawblox", "main.lua")
src = open(lua_path).read()
blob = json.dumps(course, separators=(",", ":"))
assert "]==]" not in blob
new = re.sub(r"(-- BEGIN COURSE JSON[^\n]*\n)local COURSE_JSON = \[==\[.*?\]==\]\n",
             lambda m: m.group(1) + "local COURSE_JSON = [==[" + blob + "]==]\n", src, flags=re.S)
assert new != src or blob in src, "markers not found"
open(lua_path, "w").write(new)
print("injected", len(blob), "bytes of course.json into clawblox/main.lua")
