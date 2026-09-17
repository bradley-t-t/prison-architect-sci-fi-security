# Sci-Fi Security

A Prison Architect mod. It adds laser fences and laser doors.

- Three fence styles, Laser Fence, Laser Grid and Laser Curtain, each in red or
  blue beams over grass, dirt, snow, stone, sand or concrete. They connect to
  walls and to each other like any other fence.
- Single and double Laser Doors in red or blue. A door opens from a Laser Door
  Panel while a guard stands at it, or from a triggered Door Servo, so
  prisoners cannot pass on their own.

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
| `data/materials.txt` | The fence materials, the doors and the Laser Door Panel |
| `data/tilesetpadded.png` | The game's tileset with the fence tiles added |
| `data/sprites.png` | The door and panel sprites |
| `data/scripts/` | One Lua script per door, and the panel |
| `data/prefabs.txt` | The Quick Build prefabs |
| `data/language/base-language.txt` | The names and tooltips the game shows |
| `tools/gen_assets.py` | Builds `data/` from scratch: the tileset, the sprite sheet, `materials.txt`, the prefabs and the door scripts |
| `tools/LaserDoor.lua` | The door script every door's copy is generated from |
| `tools/install.py` | Copies the mod into the game's mod folder |
