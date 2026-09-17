"""Installs the mod into the game's mods folder and enables it.

Prison Architect keeps a single tileset image, and every enabled mod that
ships data/tilesetpadded.png replaces it wholesale, so the last such mod in
the load order is the only one whose walls and fences render. This installer
therefore builds the copy it installs on top of the tileset the game would
otherwise be using: the vanilla one, overlaid in load order by every other
enabled mod that ships its own, with this mod's fence cells drawn last. The
mod is also moved to the end of the load order so its tileset is the one the
game keeps.

The mod's own data/tilesetpadded.png (built by gen_assets.py from the vanilla
tileset) is left untouched, so the mod folder stays free of other mods' art.

Usage: python install.py [path to the game's original tilesetpadded.png]
"""

import os
import re
import shutil
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_assets  # noqa: E402

ROOT = gen_assets.ROOT
MOD_NAME = "Sci-Fi Security"
INSTALL_DIR_NAME = "SciFiSecurity"
PA_DIR = os.path.join(os.environ["LOCALAPPDATA"], "Introversion", "Prison Architect")
MODS_DIR = os.path.join(PA_DIR, "mods")
PREFS = os.path.join(PA_DIR, "preferences.txt")
SHIPPED = ("manifest.txt", "thumbnail.png", "data")


def manifest_name(mod_dir):
    try:
        with open(os.path.join(mod_dir, "manifest.txt"), encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'\s*Name\s+"?([^"\r\n]+?)"?\s*$', line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return None


def read_mod_order():
    with open(PREFS, encoding="ascii", newline="") as f:
        text = f.read()
    m = re.search(r'^(Mods\s+")([^"]*)(")', text, re.M)
    mods = [x for x in m.group(2).split(",") if x]
    return text, m, mods


def enable_last():
    text, m, mods = read_mod_order()
    mods = [x for x in mods if x != MOD_NAME] + [MOD_NAME]
    text = text[:m.start()] + m.group(1) + ",".join(mods) + m.group(3) + text[m.end():]
    with open(PREFS, "w", encoding="ascii", newline="") as f:
        f.write(text)
    return mods


def other_tilesets(mods):
    """Paths of the tilesets other enabled mods ship, in load order."""
    by_name = {}
    for entry in os.listdir(MODS_DIR):
        d = os.path.join(MODS_DIR, entry)
        if os.path.isdir(d) and entry != INSTALL_DIR_NAME:
            name = manifest_name(d)
            if name:
                by_name[name] = d
    found = []
    for name in mods:
        if name == MOD_NAME or name not in by_name:
            continue
        p = os.path.join(by_name[name], "data", "tilesetpadded.png")
        if os.path.isfile(p):
            found.append((name, p))
    return found


def main():
    vanilla = sys.argv[1] if len(sys.argv) > 1 else None
    mods = enable_last()
    dest = os.path.join(MODS_DIR, INSTALL_DIR_NAME)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    for item in SHIPPED:
        src = os.path.join(ROOT, item)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, item))
        else:
            shutil.copy2(src, os.path.join(dest, item))

    # The fence blocks land wherever the base tileset has room, so the
    # installed materials.txt is regenerated to match.
    others = other_tilesets(mods)
    if others:
        base_name, base_path = others[-1]
    elif vanilla:
        base_name, base_path = "the vanilla tileset", vanilla
    else:
        base_name = base_path = None
    if base_path:
        merged, placements = gen_assets.build_tileset(base_path)
        merged.save(os.path.join(dest, "data", "tilesetpadded.png"), optimize=True)
        gen_assets.write_text_files(placements, os.path.join(dest, "data"))
        print("tileset built on top of", base_name, f"({merged.size[0]}x{merged.size[1]})")
        seen = {}
        borrowers = []
        for name, spot in placements.items():
            if spot in seen:
                borrowers.append(f"{name} (drawn with {seen[spot]})")
            else:
                seen[spot] = name
        if borrowers:
            print("no room in the tileset for:", ", ".join(borrowers))
    else:
        print("tileset copied from the mod folder")
    print("installed to", dest)
    print("load order:", ", ".join(mods))


if __name__ == "__main__":
    main()
