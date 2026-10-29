# Hosting on Mesa World

Verified (2026-10-29): "Mesa World" is the name of a Clawblox world, `worlds/mesa-island` in
https://github.com/nacloos/clawblox (called `worlds/mesa-world` in earlier commits; its world.toml says `name = "Mesa World"`).
It is the island used in the paper "Is this machine playing?". So hosting on Mesa World and hosting on Clawblox are the
same engine; there is no separate Mesa World server.

Two ways to host:
1. **Stand-alone world (done here):** `clawblox/` is a copy of the Mesa World island (from `worlds/mesa-island-wings`)
   with the race course built in. Run it with `clawblox run clawblox --port 8295 --datastore none`.
2. **Inside the stock Mesa World (not done):** paste the course-building and node-tracking sections of `clawblox/main.lua`
   into `worlds/mesa-island/main.lua`. The stock world has mesas on the island that may overlap the course; that was not checked.

`course_spec.json` is an engine-neutral export of `course.json` for any other host. Not verified: whether clawblox.com
hosts worlds publicly for outside users.
