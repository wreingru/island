# Mesa Island Race Course: agent API

Join with `POST /join?name=<bot>`, then send inputs with `POST /input` and the `X-Session` header. Read state with `GET /observe`.
Up to 5 bots per world (one heat).

## Inputs
| type | data | effect |
|---|---|---|
| `SelectModel` | `{"model": "beetle_walker" \| "flying_beetle" \| "triathlete" \| "wing_swarm" \| "curvity_scout", "speed_scale": 1, "reserve_J": 13}` | Pick the bot model while still in the start pen. `speed_scale` multiplies WalkSpeed (times are logged unscaled; divide nothing, just record the scale). |
| `Start` | `{}` | Leave the pen; the bot's race clock starts. |
| `MoveTo` | `{"position": [x, y, z]}` | Walk (or wade, in the bay) toward a point. |
| `Stop` | `{}` | Stop moving. |
| `Jump` | `{}` | Jump. |
| `Hop` | `{"to": [x, y, z], "apex": 8}` | Flying beetle only. Costs 2.61 J; refused below 1.15 x cost. Kinematic arc lasting 2.22 s / speed_scale. |

## Course (node order)
N0 start pen (-34, -44) -> N1 reef bay swim (swimmers wade the bay and round the buoy at (30.6, -45.2), then exit at the beach (24, -37); others walk the shore path from (6, -35) to (24, -35) with a 20 s penalty) -> optional N1b reef hold (walk the reef to the tip beacon (28.3, -48.5) and stay 10 s; first beetle-type bot only) -> N2 runway from z = -56 to the plane zone at z = 8 (x = -2) -> N3 plane crossing to the goal line z = 56 -> N4 drone gates D, C (on the reef), B, A: start at D's take-off pad (-26, -40), pass each gate opening in the air, or touch the red check-in pad beside its post on foot (+10 s), finish at A's landing pad (40, -29.5) -> N5 COTA loop: enter the transition pad (25, -31.5), pass the 4 checkpoints per lap (2 laps for triathletes, 1 for others), come back to the pad -> N6 hill: go through the tunnels in the ridges at z = -25 and z = -19 -> N7 summit pad (20, -10).

Transit legs between nodes are untimed.

## Observation
`player.attributes` holds `BotModel`, `RaceState` (pen / racing / finished), `CurrentNode`, `RaceClock`, `NodeLog` (JSON list of {node, enter, exit, split, mode}), `Penalties` (JSON), `GateLog` (JSON), `Laps`, `EnergyJ`, `LastActionResult`.
Server log lines starting with `RACE ` are JSON node events (NODE_ENTER, NODE_EXIT, GATE, LAP, TUNNEL, PENALTY, FINISH ...).
