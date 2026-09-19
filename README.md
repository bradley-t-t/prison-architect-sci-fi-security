# Sci-Fi Security

A Prison Architect mod. It adds laser fences and laser doors.

- Three fence styles, Laser Fence, Laser Grid and Laser Curtain, each in red or
  blue beams over grass, dirt, snow, stone, sand or concrete. They connect to
  walls and to each other like any other fence.
- Single and double Laser Doors in red or blue. A door opens for any member
  of staff who walks up to it, a cook or a workman as readily as a guard with
  keys, and shuts behind them. It never opens for a prisoner. It also opens
  from a Laser Door Panel while a guard stands at it, or from a triggered Door
  Servo.
- The Laser Door Wire Box. Build it on a Laser Door and connect a Door Control
  System, a pressure pad or a door timer to it with the Connect tool, as you
  would a Door Servo. Those can only be connected to the game's own servo, so
  the box brings one in underneath itself and covers it: the servo does the
  work and the box is what you see. A box that is dismantled uncovers its
  servo, which is dismantled like any other.
- Meals at the door during a bangup. The game brings no meals to a cell
  during a bangup, so a Laser Door on a cell does: it calls a guard, the
  guard stands at the door for a few seconds, and the prisoner is fed
  without the guard going inside. A mod cannot read the bangup itself, so
  the door goes by a prisoner at home in his cell, on no punishment, who
  last ate sixteen game hours ago or more, which no night between two meals
  reaches. A prisoner on lockdown or in solitary is left to the game, whose
  guard feeds him as he would behind any door.
- The AI Laser Controller. Build one anywhere in the prison and every Laser
  Door becomes automatic, with no guard needed: a door opens for staff and
  for prisoners going about their day and shuts behind them. The game only
  sends people where they are allowed to go, so a door still keeps a
  prisoner out of a staff-only area. A door seals itself the moment a
  misbehaving prisoner is beside it, and for a few seconds afterwards is an
  ordinary locked door that staff with keys can open. One controller runs
  every door on the map, and with none the doors are locked doors as before.

## Install

Copy the contents of this repository into a folder named `SciFiSecurity` in the
game's mod folder, then enable it under Extras, Mods.

| System | Mod folder |
| :--- | :--- |
| Windows | `%LOCALAPPDATA%\Introversion\Prison Architect\mods` |
| macOS | `~/Library/Application Support/Prison Architect/mods` |

## Layout

| Path | Holds |
| :--- | :--- |
| `manifest.txt` | The name, description and version the mod screen shows |
| `data/materials.txt` | The fence materials, the doors, the Laser Door Panel, the AI Laser Controller and the Laser Door Wire Box |
| `data/tilesetpadded.png` | The game's tileset with the fence tiles added |
| `data/sprites.png` | The door, panel and controller sprites |
| `data/scripts/` | One Lua script per door, the panel and the controller |
| `data/prefabs.txt` | The Quick Build prefabs |
| `data/jobs.txt` | The door's own job: a guard passing a meal through it |
| `data/language/base-language.txt` | The names and tooltips the game shows |
| `tools/gen_assets.py` | Builds `data/` from scratch: the tileset, the sprite sheet, `materials.txt`, the prefabs and the door scripts |
| `tools/LaserDoor.lua` | The door script every door's copy is generated from |
| `tools/install.py` | Copies the mod into the game's mod folder |
