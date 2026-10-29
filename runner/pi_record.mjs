// Record race heats as Pi session trees with @earendil-works/pi-coding-agent SessionManager.
// argv[2]: path to a JSON file {root, heats:[{heat_id, model, seed, course_id, bots:[{run_id, bot_name, nodes:[{node_id,parent_node_id,branch,data}], total_time_s}]}]}
// stdout: {run_id: {session_id, session_file, parent_session_id, parent_session_file, pi_package, entries:{node_id:{id,parentId}}}}
// No LLM runs here: entries are written straight into the session files.
import { SessionManager } from "@earendil-works/pi-coding-agent";
import { readFileSync } from "node:fs";
import path from "node:path";

const input = JSON.parse(readFileSync(process.argv[2], "utf8"));
const root = input.root;
const dir = path.join(root, "runner", "pi_sessions");
const rel = (p) => path.relative(root, p);
let pkg = "@earendil-works/pi-coding-agent";
try {
  const pj = path.join(path.dirname(new URL(import.meta.url).pathname), "node_modules", "@earendil-works", "pi-coding-agent", "package.json");
  pkg += "@" + JSON.parse(readFileSync(pj, "utf8")).version;
} catch { /* version unknown */ }
const user = (text) => ({ role: "user", content: [{ type: "text", text }], timestamp: Date.now() });
const out = {};

for (const heat of input.heats) {
  const parent = SessionManager.create(root, dir);
  parent.appendMessage(user(`Race director for heat ${heat.heat_id} (${heat.model}, seed ${heat.seed}) on ${heat.course_id}`));
  parent.appendSessionInfo?.(`race ${heat.heat_id}`);
  parent.appendCustomEntry("island-race/heat", { heat_id: heat.heat_id, model: heat.model, seed: heat.seed, course_id: heat.course_id });
  const parentFile = parent.getSessionFile();
  for (const bot of heat.bots) {
    const child = SessionManager.create(root, dir, { parentSession: rel(parentFile) });
    child.appendMessage(user(`Bot ${bot.bot_name} run ${bot.run_id}`));
    const entries = {};
    for (const n of bot.nodes) {
      if (n.parent_node_id && entries[n.parent_node_id]) child.branch(entries[n.parent_node_id].id);
      const id = child.appendCustomEntry("island-race/node", { run_id: bot.run_id, parent_node_id: n.parent_node_id, branch: n.branch, ...n.data });
      const e = child.getEntries().find((x) => x.id === id);
      entries[n.node_id] = { id, parentId: e ? e.parentId : null };
    }
    parent.appendCustomEntry("island-race/child", { run_id: bot.run_id, child_session_id: child.getSessionId(), child_session_file: rel(child.getSessionFile()), total_time_s: bot.total_time_s });
    out[bot.run_id] = { session_id: child.getSessionId(), session_file: rel(child.getSessionFile()), parent_session_id: parent.getSessionId(), parent_session_file: rel(parentFile), pi_package: pkg, entries };
  }
}
process.stdout.write(JSON.stringify(out));
