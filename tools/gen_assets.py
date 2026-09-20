"""Builds every generated file the Sci-Fi Security mod ships.

Outputs, relative to the mod root (the parent of this tools/ folder):
  data/tilesetpadded.png       the game's padded tileset with every laser fence
                               block drawn into cells the tileset leaves empty
  data/materials.txt           fence materials (with their tileset cells), the
                               doors and the panel
  data/language/base-language.txt   names and build-menu text
  data/scripts/LaserDoor*.lua  one copy of the door script per door object
  data/jobs.txt                the door's own job, a guard passing a meal through it
  data/prefabs.txt             the Laser Cell Block quick build
  data/sprites.png             door and panel sprites
  tools/card-art.png           the art on the mod's Workshop card; thumbnail.png is exported from Figma
  tools/preview.png            every fence cell, the doors and the panel

Usage: python gen_assets.py <path to the game's original tilesetpadded.png>

The fence set is every combination of style (Fence, Grid, Curtain), beam colour
(Red, Blue) and ground (Grass, Dirt, Snow, Stone, Sand, Concrete). Fence tiles carry
their ground because the game draws nothing under a wall tile; the ground is
cropped from the game's own floor tiles so it matches the floor around it.
"""

import os
import shutil
import sys

from PIL import Image, ImageDraw


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TOOLS = os.path.join(ROOT, "tools")

# The padded tileset is 64 cells of 72 px; each cell holds a 64 px tile with a
# 4 px bleed on every side.
CELL = 72
PAD = 4
TILE = 64
GRID = 64

# The game's connected-wall layout, read off its own wall blocks: for every
# cell of the 7x4 block, which sides the wall runs to. "full" runs to the tile
# edge; "stub" is a wall end drawn just short of the edge.
BLOCK_W = 7
BLOCK_H = 4
LAYOUT = {
    (0, 0): dict(N=1, S=1), (1, 0): dict(W="full", E="full"),
    (2, 0): dict(S=1, E="full"), (3, 0): dict(S=1, W="full"),
    (4, 0): dict(S=1, W="full", E="full"), (5, 0): dict(S=1, W="stub", E="full"),
    (6, 0): dict(S=1, W="full", E="stub"),
    (0, 1): dict(S=1), (1, 1): dict(W="stub", E="full"),
    (2, 1): dict(N=1, E="full"), (3, 1): dict(N=1, W="full"),
    (4, 1): dict(N=1, W="full", E="full"), (5, 1): dict(N=1, W="stub", E="full"),
    (6, 1): dict(N=1, W="full", E="stub"),
    (0, 2): dict(N=1), (1, 2): dict(W="full", E="stub"),
    (2, 2): dict(S=1, E="stub"), (3, 2): dict(S=1, W="stub"),
    (4, 2): dict(N=1, S=1, E="full"), (5, 2): dict(N=1, S=1, W="full"),
    (6, 2): dict(N=1, S=1, W="full", E="full"),
    (2, 3): dict(N=1, E="stub"), (3, 3): dict(N=1, W="stub"),
}

COLOURS = {
    "Red": dict(core=(255, 72, 72), hot=(255, 205, 205), halo=(180, 24, 24), glow=(110, 14, 14)),
    "Blue": dict(core=(72, 165, 255), hot=(205, 235, 255), halo=(22, 78, 190), glow=(12, 40, 110)),
}

STEEL = (150, 156, 164)
STEEL_HI = (196, 201, 208)
STEEL_LO = (104, 110, 118)
DARK = (44, 48, 54)
DARK_HI = (66, 71, 78)
CONCRETE = (118, 124, 132)
CONCRETE_HI = (152, 157, 164)
CONCRETE_LO = (84, 89, 96)
LAMP = (255, 176, 32, 255)

STYLES = {
    "Fence": dict(label="Laser Fence", price=40, time=10.0),
    "Grid": dict(label="Laser Grid Fence", price=60, time=12.0),
    "Curtain": dict(label="Laser Curtain Fence", price=50, time=10.0),
}
# Tileset cell of the game's floor material each ground is cropped from.
GROUND_CELLS = {"Grass": (0, 4), "Dirt": (5, 4), "Snow": (47, 34), "Stone": (25, 4), "Sand": (15, 10),
                "Concrete": (20, 6)}
# Also the packing order: when the tileset runs out of room, the last
# combinations are the ones that fall back to another block's art.
GROUND_ORDER = ["Grass", "Dirt", "Snow", "Stone", "Sand", "Concrete"]

# Doors have nine sprites. Frames 0 to 2 are the sealed door with its beams
# pulsing, and frame 8 is the same frame with its beams off, which is the open
# and the broken door. The engine draws a door at its position plus OpenDir
# times its openness; the door script holds OpenDir at zero, so none of those
# four ever moves.
#
# Frames 3 to 7 are what the script falls back to if it cannot hold OpenDir.
# The engine then slides the sprite 0.9 of a door width along the wall as the
# door opens, so each open frame holds the frame and housing (no beams) drawn
# one slide to one side, and the slide carries it back into the doorway. The
# slide runs a quarter turn on from the way the door faces, so which frame is
# right depends on how the door was rotated; the script picks. That is why
# every flat open frame is three door widths wide, centred on the door: the
# game draws sprites wider than their object centred at full size, the way its
# own metal detector is.
DOOR_FRAMES = 9
OPEN_FRAME_LEFT = 3
OPEN_FRAME_RIGHT = 4
# Frame 5 is empty. The script shows it on any tick where the engine reports
# the door part-way open, so a sliding sprite is never drawn.
TRANSITION_FRAME = 5
# Frames 6 and 7 are the open frames a door standing in a north-south wall
# uses, pre-shifted down and up respectively. A flat door never shows them.
OPEN_FRAME_DOWN = 6
OPEN_FRAME_UP = 7
# Frame 8 is the frame at rest with its beams off.
REST_FRAME = 8
DOORS = [
    # name, colour, width in tiles, price, and a column no longer read: where a
    # frame sits on sprites.png is worked out by pack_sheet()
    ("LaserDoorRed", "Red", 1, 600, 0),
    ("LaserDoorBlue", "Blue", 1, 600, 6),
    ("LaserDoorLargeRed", "Red", 2, 900, 12),
    ("LaserDoorLargeBlue", "Blue", 2, 900, 24),
]
# The engine does not rotate a sprite that rotates with the wall; it reads
# pre-drawn orientations from fixed spots beside the base sprite (x, y, w, h):
# the 180-degree version at (x + w, y), and the 90 and 270-degree versions,
# h wide and w tall, at (x + 2w, y + h - w) and (x + 2w + h, y + h - w), so
# their bottoms line up with the base sprite. Every door frame is laid out
# that way in a band w rows tall, with the base sprite on the band's last
# two rows. A frame's stride along the sheet is therefore 2w + 2h cells.
#
# A sprite taller than its object is not centred the way a wide one is: it
# hangs upward from the tile (TopAligned false) or downward from it
# (TopAligned true). The vertical door versions are taller than the door,
# so the door body sits at the bottom of its canvas and the open frame that
# is pre-shifted upward fits above it. The open frame pre-shifted downward
# is the one sprite marked TopAligned true: its canvas hangs downward, its
# base sprite sits on the band's first two rows, and the engine reads its
# vertical versions level with that base.
# A door draws nothing outside its own frame: the only beams that come and
# go with it are the ones between its posts.
# Panel sprites: idle, lamp on, lamp off (the last two alternate while a guard
# is at the panel).
PANEL_FRAMES = 3
# Measured in game on the large door: the engine slides a door by its width
# less 12 px (in the tile's own 64 px), so the pre-shifted open frames are
# drawn that much short of a full door width. The single door slides by its
# width less 6 px, the same proportion.
OPEN_SLIDE_EXTRA = {1: -6, 2: -12}
# Seconds a door shows its empty frame after changing state. The single door
# opens within one script update, so the renderer's catch-up slide would
# otherwise show; the large door takes several updates and needs none.
SETTLE_SECONDS = {1: 0.3, 2: 0.0}
# How far from its middle a door looks for staff: a double door's middle is
# half a tile further from whoever stands at one of its ends.
STAFF_REACH = {1: 1.5, 2: 2.0}
# Every frame has its own canvas, and the canvas is also the door's hit box,
# so a frame is only as large as it has to be. Sealed and rest frames are
# exactly the door. The flat open frames hold the frame shifted one slide to
# either side, so they are three door widths wide, centred on the door. The
# vertical-only open frames show nothing flat; their width sets the height
# of their vertical versions, a door plus one slide, hanging up or down.
PANEL_STRIDE = 8
# The AI Laser Controller sits in the panel's band, past the panel's frames.
# It never rotates, so each frame is one picture two cells wide.
CONTROLLER_FRAMES = 2
CONTROLLER_X0 = PANEL_STRIDE * 3
# The Laser Door Wire Box is one picture, past the controller's frames.
WIRE_BOX_X0 = CONTROLLER_X0 + 2 * CONTROLLER_FRAMES


def door_frame_cells(door, frame):
    """Width in 32 px cells of a frame's flat sprite."""
    tiles = door[2]
    if frame in (OPEN_FRAME_LEFT, OPEN_FRAME_RIGHT):
        return 6 * tiles
    if frame in (OPEN_FRAME_DOWN, OPEN_FRAME_UP):
        return 4 * tiles
    return 2 * tiles


def door_frame_stride(door, frame):
    """Cells a frame takes along the sheet: its four orientations."""
    return 2 * door_frame_cells(door, frame) + 4


def door_frame_top_aligned(frame):
    return frame == OPEN_FRAME_DOWN


# Every mod's sprites share one atlas in the game, so the sheet is packed as
# tightly as the engine allows. The engine reads a frame's four facings from
# fixed spots: two flat ones side by side, then two vertical ones, as tall as
# the flat frame is wide. That is an L of four rectangles with a hole in its
# corner, and the next frame's rectangles go in the hole: frames are placed
# rectangle by rectangle, largest first, at the first spot on the sheet where
# none of their four touches one already placed. A rectangle that draws
# nothing (the part-way frame, and the flat facings of the two frames that
# only ever show vertically) is just as empty wherever it is read from, so
# empty rectangles may lie over one another, though never over a drawn one.
# The panel, controller and wire box are a strip two cells high. Both sides of
# the sheet come out a multiple of 64 px, two cells, which the game's atlas
# wants.
PANEL_STRIP_CELLS = PANEL_STRIDE * PANEL_FRAMES + 2 * CONTROLLER_FRAMES + 2


def frame_rects(door, frame):
    """A frame's four rectangles (x, y, w, h) from the corner of its block."""
    w = door_frame_cells(door, frame)
    rows = max(2, w)
    flat_y = 0 if door_frame_top_aligned(frame) else rows - 2
    return [(0, flat_y, w, 2), (w, flat_y, w, 2), (2 * w, 0, 2, w), (2 * w + 2, 0, 2, w)]


def frame_draws(door, frame):
    """Whether each of a frame's four rectangles has anything drawn in it."""
    _, colour, tiles, _, _ = door
    flat = door_sprite(COLOURS[colour], tiles, frame).getbbox() is not None
    tall = door_sprite_vertical(COLOURS[colour], tiles, frame).getbbox() is not None
    return [flat, flat, tall, tall]


def pack_into(width, items):
    drawn = [[False] * width for _ in range(400)]
    blank = [[False] * width for _ in range(400)]
    origins = {}
    for key, rects, draws in items:
        reach = max(x + w for x, _, w, _ in rects)
        if reach > width:
            return None

        def fits(ox, oy):
            for (x, y, w, h), solid in zip(rects, draws):
                for j in range(oy + y, oy + y + h):
                    for i in range(ox + x, ox + x + w):
                        if drawn[j][i] or (solid and blank[j][i]):
                            return False
            return True

        spot = next(((ox, oy) for oy in range(0, 380, 2) for ox in range(0, width - reach + 1, 2) if fits(ox, oy)))
        for (x, y, w, h), solid in zip(rects, draws):
            grid = drawn if solid else blank
            for j in range(spot[1] + y, spot[1] + y + h):
                for i in range(spot[0] + x, spot[0] + x + w):
                    grid[j][i] = True
        origins[key] = spot
    rows = max(j for j in range(400) if any(drawn[j]) or any(blank[j])) + 1
    return origins, rows + rows % 2


def pack_sheet():
    items = [((door[0], f), frame_rects(door, f), frame_draws(door, f)) for door in DOORS for f in range(DOOR_FRAMES)]
    items.append(("strip", [(0, 0, PANEL_STRIP_CELLS, 2)], [True]))
    items.sort(key=lambda it: -sum(w * h for (_, _, w, h), solid in zip(it[1], it[2]) if solid))
    best = None
    for width in range(PANEL_STRIP_CELLS + PANEL_STRIP_CELLS % 2, 130, 2):
        packed = pack_into(width, items)
        if packed and (best is None or width * packed[1] < best[0]):
            best = (width * packed[1], width, packed)
    return best[1], best[2][0], best[2][1]


_ORIGINS = None
SHEET_CELLS = PANEL_X0 = PANEL_BAND = None      # set by layout()


def layout():
    """Packed on first use: the door pictures it measures are drawn by
    functions further down this file."""
    global _ORIGINS, SHEET_CELLS, PANEL_X0, PANEL_BAND
    if _ORIGINS is None:
        width, _ORIGINS, rows = pack_sheet()
        SHEET_CELLS = (width, rows)
        PANEL_X0, PANEL_BAND = _ORIGINS["strip"]
    return _ORIGINS


def door_frame_cell(door, frame):
    """Cell of a frame's base (east-west) sprite. A base sits on its block's
    last two rows so its vertical versions fit above it, except the
    top-aligned frame, whose base sits on the block's first two rows with its
    vertical versions below."""
    x, y = layout()[(door[0], frame)]
    return x, y + frame_rects(door, frame)[0][1]


def door_frame_vertical_row(door, frame):
    """Top row of a frame's vertical versions, which fill the block's height."""
    return layout()[(door[0], frame)][1]


# ---------------------------------------------------------------- grounds

_ground_source = None
_ground_cache = {}


def set_ground_source(tileset_path):
    """The tileset the grounds are cropped from. The game's floor cells sit at
    the same place in every mod's tileset, so any full tileset will do."""
    global _ground_source, _ground_cache
    _ground_source = tileset_path
    _ground_cache = {}


def ground(name):
    if name not in _ground_cache:
        if _ground_source is None:
            raise RuntimeError("set_ground_source() must be called before drawing tiles")
        ts = Image.open(_ground_source).convert("RGBA")
        cx, cy = GROUND_CELLS[name]
        _ground_cache[name] = ts.crop((cx * CELL + PAD, cy * CELL + PAD, cx * CELL + PAD + TILE, cy * CELL + PAD + TILE))
    return _ground_cache[name].copy()


# ---------------------------------------------------------------- beams

def overlay(w=TILE, h=TILE):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def hbeam(ov, x0, x1, y, col, strength=1.0):
    if x1 <= x0:
        return
    d = ImageDraw.Draw(ov)
    a = lambda v: int(v * strength)
    d.line([(x0, y - 1), (x1, y - 1)], fill=col["halo"] + (a(120),))
    d.line([(x0, y + 1), (x1, y + 1)], fill=col["halo"] + (a(120),))
    d.line([(x0, y - 2), (x1, y - 2)], fill=col["glow"] + (a(60),))
    d.line([(x0, y + 2), (x1, y + 2)], fill=col["glow"] + (a(60),))
    d.line([(x0, y), (x1, y)], fill=col["core"] + (a(255),))
    mid0 = x0 + (x1 - x0) // 4
    mid1 = x1 - (x1 - x0) // 4
    d.line([(mid0, y), (mid1, y)], fill=col["hot"] + (a(170),))


def vbeam(ov, x, y0, y1, col, strength=1.0):
    if y1 <= y0:
        return
    d = ImageDraw.Draw(ov)
    a = lambda v: int(v * strength)
    d.line([(x - 1, y0), (x - 1, y1)], fill=col["halo"] + (a(120),))
    d.line([(x + 1, y0), (x + 1, y1)], fill=col["halo"] + (a(120),))
    d.line([(x - 2, y0), (x - 2, y1)], fill=col["glow"] + (a(60),))
    d.line([(x + 2, y0), (x + 2, y1)], fill=col["glow"] + (a(60),))
    d.line([(x, y0), (x, y1)], fill=col["core"] + (a(255),))
    mid0 = y0 + (y1 - y0) // 4
    mid1 = y1 - (y1 - y0) // 4
    d.line([(x, mid0), (x, mid1)], fill=col["hot"] + (a(170),))


def floor_glow(ov, arms, col):
    """A wash on the ground under the beams that fades out sideways. Along
    the beam it runs past the tile edge so neighbouring tiles join without a
    seam."""
    d = ImageDraw.Draw(ov)
    # outermost band first, brightest core last
    bands = ((8, 18), (5, 40), (3, 70), (0, 105))
    for grow, alpha in bands:
        c = col["glow"] + (alpha,)
        if arms.get("W"):
            d.rectangle([-8, 51 - grow, 32, 59 + grow], fill=c)
        if arms.get("E"):
            d.rectangle([32, 51 - grow, TILE + 8, 59 + grow], fill=c)
        if arms.get("N"):
            d.rectangle([27 - grow, -8, 37 + grow, 32], fill=c)
        if arms.get("S"):
            d.rectangle([27 - grow, 32, 37 + grow, TILE + 8], fill=c)


def arm_span(arms):
    """Pixel extents of the W and E beam runs for a cell."""
    w0 = None
    if arms.get("W") == "full":
        w0 = 0
    elif arms.get("W") == "stub":
        w0 = 7
    e1 = None
    if arms.get("E") == "full":
        e1 = TILE - 1
    elif arms.get("E") == "stub":
        e1 = 56
    return w0, e1


def end_post(d, side, color, hi, lo, y0=18, y1=54):
    if side == "E":
        d.rectangle([57, y0, 61, y1], fill=color)
        d.line([(57, y0), (57, y1)], fill=hi)
        d.line([(61, y0), (61, y1)], fill=lo)
        d.rectangle([56, y0 - 3, 62, y0], fill=hi)
    else:
        d.rectangle([2, y0, 6, y1], fill=color)
        d.line([(2, y0), (2, y1)], fill=hi)
        d.line([(6, y0), (6, y1)], fill=lo)
        d.rectangle([1, y0 - 3, 7, y0], fill=hi)


def node(d, x, y, col):
    d.rectangle([x, y, x + 1, y + 1], fill=col["hot"] + (255,))


def ns_beams(im, arms, col, lines):
    """North-south beams run the full tile height over the post so a run of
    tiles reads as one unbroken line. Callers redraw the post cap afterwards."""
    ns = overlay()
    for x, s in lines:
        if arms.get("N"):
            vbeam(ns, x, 0, 32, col, s)
        if arms.get("S"):
            vbeam(ns, x, 32, TILE - 1, col, s)
    im.alpha_composite(ns)


# ---------------------------------------------------------------- styles

def tile_fence(arms, col, gnd):
    """Steel posts with stacked emitters and four horizontal beams."""
    im = ground(gnd)
    ov = overlay()
    floor_glow(ov, arms, col)
    heights = [19, 29, 39, 49]
    w0, e1 = arm_span(arms)
    for y in heights:
        if w0 is not None:
            hbeam(ov, w0, 28, y, col)
        if e1 is not None:
            hbeam(ov, 36, e1, y, col)
    im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    d.rectangle([24, 54, 40, 59], fill=(18, 20, 24, 255))
    d.rectangle([28, 14, 36, 56], fill=STEEL + (255,))
    d.line([(28, 14), (28, 56)], fill=STEEL_HI + (255,))
    d.rectangle([34, 14, 36, 56], fill=STEEL_LO + (255,))
    ns_beams(im, arms, col, ((29, 0.6), (32, 1.0), (35, 0.6)))
    d = ImageDraw.Draw(im)
    d.rectangle([26, 10, 38, 16], fill=STEEL_HI + (255,))
    d.line([(26, 10), (38, 10)], fill=(222, 225, 230, 255))
    d.rectangle([30, 8, 34, 10], fill=LAMP)
    if any(arms.values()):
        for y in heights:
            if w0 is not None:
                node(d, 26, y - 1, col)
            if e1 is not None:
                node(d, 37, y - 1, col)
    if arms.get("E") == "stub":
        end_post(d, "E", STEEL + (255,), STEEL_HI + (255,), STEEL_LO + (255,))
    if arms.get("W") == "stub":
        end_post(d, "W", STEEL + (255,), STEEL_HI + (255,), STEEL_LO + (255,))
    return im


def tile_grid(arms, col, gnd):
    """Concrete pylons framing a crosshatch of beams."""
    im = ground(gnd)
    ov = overlay()
    floor_glow(ov, arms, col)
    heights = [17, 25, 33, 41, 49]
    w0, e1 = arm_span(arms)
    for y in heights:
        if w0 is not None:
            hbeam(ov, w0, 24, y, col)
        if e1 is not None:
            hbeam(ov, 40, e1, y, col)
    if w0 is not None:
        for x in (8, 16):
            if x > w0:
                vbeam(ov, x, 17, 49, col, 0.6)
    if e1 is not None:
        for x in (48, 56):
            if x < e1:
                vbeam(ov, x, 17, 49, col, 0.6)
    im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    d.rectangle([22, 56, 42, 61], fill=(18, 20, 24, 255))
    d.rectangle([24, 10, 40, 58], fill=CONCRETE + (255,))
    d.rectangle([24, 10, 25, 58], fill=CONCRETE_HI + (255,))
    d.rectangle([38, 10, 40, 58], fill=CONCRETE_LO + (255,))
    d.rectangle([24, 50, 40, 58], fill=DARK + (255,))
    d.rectangle([28, 52, 36, 54], fill=col["core"] + (255,))
    ns_beams(im, arms, col, ((26, 0.5), (29, 0.8), (32, 1.0), (35, 0.8), (38, 0.5)))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 10, 40, 14], fill=CONCRETE_HI + (255,))
    if any(arms.values()):
        for y in heights:
            if w0 is not None:
                node(d, 22, y - 1, col)
            if e1 is not None:
                node(d, 41, y - 1, col)
    if arms.get("E") == "stub":
        end_post(d, "E", CONCRETE + (255,), CONCRETE_HI + (255,), CONCRETE_LO + (255,), 14, 56)
    if arms.get("W") == "stub":
        end_post(d, "W", CONCRETE + (255,), CONCRETE_HI + (255,), CONCRETE_LO + (255,), 14, 56)
    return im


def tile_curtain(arms, col, gnd):
    """A ground rail and head rail on slim stanchions, with a curtain of
    vertical beams between them."""
    im = ground(gnd)
    ov = overlay()
    floor_glow(ov, arms, col)
    w0, e1 = arm_span(arms)
    d0 = ImageDraw.Draw(ov)
    if w0 is not None:
        d0.rectangle([w0, 12, 30, 16], fill=DARK + (255,))
        d0.rectangle([w0, 50, 30, 58], fill=DARK + (255,))
        d0.line([(w0, 12), (30, 12)], fill=DARK_HI + (255,))
        d0.line([(w0, 53), (30, 53)], fill=col["core"] + (230,))
    if e1 is not None:
        d0.rectangle([34, 12, e1, 16], fill=DARK + (255,))
        d0.rectangle([34, 50, e1, 58], fill=DARK + (255,))
        d0.line([(34, 12), (e1, 12)], fill=DARK_HI + (255,))
        d0.line([(34, 53), (e1, 53)], fill=col["core"] + (230,))
    if arms.get("N"):
        d0.rectangle([26, 0, 29, 30], fill=DARK + (255,))
        d0.rectangle([35, 0, 38, 30], fill=DARK + (255,))
        d0.line([(27, 0), (27, 30)], fill=col["core"] + (200,))
        d0.line([(37, 0), (37, 30)], fill=col["core"] + (200,))
    if arms.get("S"):
        d0.rectangle([26, 34, 29, TILE - 1], fill=DARK + (255,))
        d0.rectangle([35, 34, 38, TILE - 1], fill=DARK + (255,))
        d0.line([(27, 34), (27, TILE - 1)], fill=col["core"] + (200,))
        d0.line([(37, 34), (37, TILE - 1)], fill=col["core"] + (200,))
    if w0 is not None:
        x = 27
        while x > w0 + 1:
            vbeam(ov, x, 16, 50, col, 0.85)
            x -= 6
    if e1 is not None:
        x = 37
        while x < e1 - 1:
            vbeam(ov, x, 16, 50, col, 0.85)
            x += 6
    im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    d.rectangle([28, 55, 36, 59], fill=(18, 20, 24, 255))
    d.rectangle([30, 12, 34, 56], fill=STEEL + (255,))
    d.line([(30, 12), (30, 56)], fill=STEEL_HI + (255,))
    d.line([(34, 12), (34, 56)], fill=STEEL_LO + (255,))
    ns_beams(im, arms, col, ((30, 0.5), (32, 1.0), (34, 0.5)))
    d = ImageDraw.Draw(im)
    d.rectangle([29, 9, 35, 12], fill=STEEL_HI + (255,))
    d.rectangle([31, 7, 33, 9], fill=LAMP)
    if arms.get("E") == "stub":
        end_post(d, "E", STEEL + (255,), STEEL_HI + (255,), STEEL_LO + (255,), 12, 56)
    if arms.get("W") == "stub":
        end_post(d, "W", STEEL + (255,), STEEL_HI + (255,), STEEL_LO + (255,), 12, 56)
    return im


STYLE_DRAW = {"Fence": tile_fence, "Grid": tile_grid, "Curtain": tile_curtain}


def fence_defs():
    """Every fence material: name, style, colour, ground, display label."""
    out = []
    for style, meta in STYLES.items():
        for colour in COLOURS:
            for gnd in GROUND_ORDER:
                out.append(dict(
                    name=f"Laser{style}{colour}{gnd}", style=style, colour=colour, ground=gnd,
                    label=f"{meta['label']} ({colour}, {gnd})", price=meta["price"], time=meta["time"]))
    return out


# ---------------------------------------------------------------- objects

def door_sprite(col, tiles, frame=0):
    """A frame's flat (east-west) sprite. Sealed and rest frames are the
    door itself. The flat open frames carry the beamless frame shifted one
    slide left or right of centre, so the engine's slide lands it back in
    the doorway. The other frames have nothing to show flat."""
    dw = TILE * tiles
    width = door_frame_cells(("", "", tiles, 0, 0), frame) * 32
    slide = dw + OPEN_SLIDE_EXTRA[tiles]
    im = Image.new("RGBA", (width, TILE), (0, 0, 0, 0))
    centre = (width - dw) // 2
    if frame < OPEN_FRAME_LEFT:
        im.paste(door_body(col, tiles, frame), (0, 0))
    elif frame == REST_FRAME:
        im.paste(door_body(col, tiles, 0, beams=False), (0, 0))
    elif frame == OPEN_FRAME_LEFT:
        im.paste(door_body(col, tiles, 0, beams=False), (centre - slide, 0))
    elif frame == OPEN_FRAME_RIGHT:
        im.paste(door_body(col, tiles, 0, beams=False), (centre + slide, 0))
    return im


def door_sprite_vertical(col, tiles, frame=0):
    """A frame's vertical (north-south wall) sprite, one tile wide. Sealed
    and rest frames are the door itself. The vertical-only open frames
    carry the beamless frame shifted one slide from the tile: the top-aligned
    one hangs down from the tile with the frame below, the other hangs up
    with the frame above. The flat open frames have nothing to show here."""
    dw = TILE * tiles
    height = door_frame_cells(("", "", tiles, 0, 0), frame) * 32
    slide = dw + OPEN_SLIDE_EXTRA[tiles]
    im = Image.new("RGBA", (TILE, height), (0, 0, 0, 0))
    if frame < OPEN_FRAME_LEFT:
        im.paste(door_body_vertical(col, tiles, frame), (0, 0))
    elif frame == REST_FRAME:
        im.paste(door_body_vertical(col, tiles, 0, beams=False), (0, 0))
    elif frame == OPEN_FRAME_DOWN:
        im.paste(door_body_vertical(col, tiles, 0, beams=False), (0, slide))
    elif frame == OPEN_FRAME_UP:
        im.paste(door_body_vertical(col, tiles, 0, beams=False), (0, height - dw - slide))
    return im


def door_body_vertical(col, tiles, frame=0, beams=True):
    dw = TILE * tiles
    im = Image.new("RGBA", (TILE, dw), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # end posts across the wall's thickness, the north one carrying the housing
    for y0 in (0, dw - 8):
        d.rectangle([20, y0, 43, y0 + 7], fill=STEEL + (255,))
        d.line([(20, y0), (43, y0)], fill=STEEL_HI + (255,))
        d.line([(20, y0 + 7), (43, y0 + 7)], fill=STEEL_LO + (255,))
    d.rectangle([22, 8, 41, 12], fill=(58, 62, 70, 255))
    xs = (26, 30, 34, 38)
    if not beams:
        for x in xs:
            d.rectangle([x - 1, 8, x + 1, 9], fill=col["glow"] + (255,))
            d.rectangle([x - 1, dw - 10, x + 1, dw - 9], fill=col["glow"] + (255,))
        return im
    ov = overlay(TILE, dw)
    o = ImageDraw.Draw(ov)
    o.rectangle([22, 8, 41, dw - 9], fill=col["glow"] + (80,))
    strengths = (1.0, 0.8, 0.62)
    for i, x in enumerate(xs):
        vbeam(ov, x, 13, dw - 9, col, strengths[(i + frame) % 3])
        y = 16 + ((i * 11 + frame * 12) % max(1, dw - 30))
        o.line([(x, y), (x, y + 4)], fill=col["hot"] + (255,))
    im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    for x in xs:
        d.rectangle([x - 1, 8, x + 1, 9], fill=col["hot"] + (255,))
        d.rectangle([x - 1, dw - 10, x + 1, dw - 9], fill=col["hot"] + (255,))
    return im


def door_body(col, tiles, frame=0, beams=True):
    """The door itself: an emitter housing across the top, a steel post at
    each end, and, when sealed, beams running from the housing straight down
    to the floor over whatever floor the doorway has."""
    w = TILE * tiles
    im = Image.new("RGBA", (w, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([8, 0, w - 9, 12], fill=(58, 62, 70, 255))
    d.line([(8, 0), (w - 9, 0)], fill=(90, 95, 104, 255))
    d.line([(8, 12), (w - 9, 12)], fill=(40, 43, 49, 255))
    for x0 in (0, w - 8):
        d.rectangle([x0, 0, x0 + 7, 63], fill=STEEL + (255,))
        d.line([(x0, 0), (x0, 63)], fill=STEEL_HI + (255,))
        d.line([(x0 + 7, 0), (x0 + 7, 63)], fill=STEEL_LO + (255,))
        d.rectangle([x0, 0, x0 + 7, 3], fill=STEEL_HI + (255,))
    xs = list(range(14, w - 12, 7))
    if not beams:
        for x in xs:
            d.rectangle([x - 1, 10, x + 1, 12], fill=col["glow"] + (255,))
        return im
    ov = overlay(w, TILE)
    o = ImageDraw.Draw(ov)
    # a wash that fades toward the floor, strongest under the housing
    for y0, alpha in ((13, 70), (30, 45), (46, 25)):
        o.rectangle([8, y0, w - 9, 63], fill=col["glow"] + (alpha,))
    o.line([(9, 5), (w - 10, 5)], fill=col["core"] + (230,))
    strengths = (1.0, 0.8, 0.62)
    for i, x in enumerate(xs):
        vbeam(ov, x, 13, 61, col, strengths[(i + frame) % 3])
        # a bright pulse travelling down each beam
        y = 16 + ((i * 9 + frame * 12) % 42)
        o.line([(x, y), (x, y + 4)], fill=col["hot"] + (255,))
        # the spot where the beam meets the floor
        o.rectangle([x - 2, 60, x + 2, 63], fill=col["halo"] + (160,))
    im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    for x in xs:
        d.rectangle([x - 1, 10, x + 1, 12], fill=col["hot"] + (255,))
        d.rectangle([x - 1, 61, x + 1, 62], fill=col["hot"] + (255,))
    return im


def panel_sprite(frame=0):
    """A free-standing console, bottom-aligned in its tile. Frame 0 is idle;
    frames 1 and 2 are the lit and dark halves of the status lamp's blink."""
    im = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([12, 58, 52, 62], fill=(0, 0, 0, 90))
    d.rectangle([20, 40, 44, 60], fill=DARK + (255,))
    d.rectangle([20, 40, 22, 60], fill=DARK_HI + (255,))
    d.rectangle([14, 58, 50, 61], fill=(30, 33, 38, 255))
    d.polygon([(8, 22), (56, 22), (60, 44), (4, 44)], fill=(74, 80, 88, 255))
    d.polygon([(8, 22), (56, 22), (57, 26), (7, 26)], fill=(104, 110, 118, 255))
    d.line([(4, 44), (60, 44)], fill=(52, 57, 64, 255))
    d.rectangle([12, 27, 38, 41], fill=(16, 40, 80, 255))
    d.rectangle([13, 28, 37, 40], fill=(26, 78, 140, 255))
    for y in (31, 34, 37):
        d.line([(15, y), (30, y)], fill=(120, 190, 255, 255))
    d.rectangle([32, 30, 35, 38], fill=(72, 165, 255, 255))
    for x in (43, 47, 51):
        for y in (29, 33, 37):
            d.rectangle([x, y, x + 2, y + 2], fill=(150, 156, 164, 255))
    if frame == 1:
        d.rectangle([43, 40, 51, 43], fill=(72, 165, 255, 255))
        d.rectangle([44, 41, 50, 42], fill=(205, 235, 255, 255))
        d.rectangle([13, 28, 37, 40], fill=(40, 110, 190, 255))
        for y in (31, 34, 37):
            d.line([(15, y), (30, y)], fill=(170, 215, 255, 255))
    elif frame == 2:
        d.rectangle([44, 41, 50, 42], fill=(22, 78, 190, 255))
    else:
        d.rectangle([44, 41, 50, 42], fill=(255, 72, 72, 255))
    return im


def controller_sprite(frame=0):
    """A server cabinet seen from the front, bottom-aligned in its tile: a
    dark case, a column of drive lights, and a blue eye that is lit in frame
    0 and dim in frame 1."""
    im = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([10, 58, 54, 62], fill=(0, 0, 0, 90))
    d.rectangle([12, 6, 51, 60], fill=DARK + (255,))
    d.rectangle([12, 6, 51, 8], fill=DARK_HI + (255,))
    d.rectangle([12, 6, 14, 60], fill=DARK_HI + (255,))
    d.rectangle([49, 6, 51, 60], fill=(30, 33, 38, 255))
    d.rectangle([17, 11, 46, 31], fill=(16, 40, 80, 255))
    lit = frame == 0
    d.ellipse([24, 13, 39, 28], fill=(26, 78, 140, 255))
    d.ellipse([27, 16, 36, 25], fill=(72, 165, 255, 255) if lit else (22, 78, 190, 255))
    if lit:
        d.ellipse([29, 17, 33, 21], fill=(205, 235, 255, 255))
    for i, y in enumerate(range(36, 56, 5)):
        d.rectangle([17, y, 46, y + 2], fill=(30, 33, 38, 255))
        on = (i + frame) % 2 == 0
        d.rectangle([19, y, 21, y + 2], fill=(84, 220, 120, 255) if on else (24, 120, 60, 255))
        d.rectangle([24, y, 26, y + 2], fill=(72, 165, 255, 255) if not on else (22, 78, 190, 255))
    return im


def wire_box_sprite():
    """A small junction box seen from above, centred in its tile and wide
    enough to cover the Door Servo underneath it whichever way that faces:
    a dark lid, a blue lamp, and a cable leaving each side."""
    im = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([2, 30, 12, 33], fill=(30, 33, 38, 255))
    d.rectangle([51, 30, 61, 33], fill=(30, 33, 38, 255))
    d.rectangle([13, 15, 52, 52], fill=(0, 0, 0, 90))
    d.rectangle([12, 12, 51, 49], fill=DARK + (255,))
    d.rectangle([12, 12, 51, 14], fill=DARK_HI + (255,))
    d.rectangle([12, 12, 14, 49], fill=DARK_HI + (255,))
    d.rectangle([49, 12, 51, 49], fill=(30, 33, 38, 255))
    d.rectangle([12, 47, 51, 49], fill=(30, 33, 38, 255))
    for x, y in ((16, 16), (45, 16), (16, 43), (45, 43)):
        d.rectangle([x, y, x + 2, y + 2], fill=(30, 33, 38, 255))
    d.ellipse([26, 25, 37, 36], fill=(22, 78, 190, 255))
    d.ellipse([28, 27, 35, 34], fill=(72, 165, 255, 255))
    d.rectangle([30, 28, 32, 30], fill=(205, 235, 255, 255))
    return im


# ---------------------------------------------------------------- tileset

def padded(tile):
    cell = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    cell.paste(tile, (PAD, PAD))
    for x in range(PAD):
        cell.paste(cell.crop((PAD, 0, PAD + 1, CELL)), (x, 0))
        cell.paste(cell.crop((PAD + TILE - 1, 0, PAD + TILE, CELL)), (PAD + TILE + x, 0))
    for y in range(PAD):
        cell.paste(cell.crop((0, PAD, CELL, PAD + 1)), (0, y))
        cell.paste(cell.crop((0, PAD + TILE - 1, CELL, PAD + TILE)), (0, PAD + TILE + y))
    return cell


def occupied_cells(ts):
    alpha = ts.getchannel("A")
    rows = ts.size[1] // CELL
    used = set()
    for cy in range(rows):
        for cx in range(GRID):
            if alpha.crop((cx * CELL, cy * CELL, (cx + 1) * CELL, (cy + 1) * CELL)).getbbox():
                used.add((cx, cy))
    return used


SHAPE = sorted(LAYOUT.keys())


def pack_blocks(ts, count):
    """Top-left cells for up to `count` fence blocks inside the game's 64
    rows. A block only occupies the 23 cells its layout uses, so blocks
    interlock where the tileset is tight. The tileset must keep its size:
    the game maps tiles assuming 64 rows, and a taller image shifts every
    tile on the map. Fewer spots than asked for means the tileset is full."""
    used = occupied_cells(ts)
    spots = []
    for cy in range(GRID - BLOCK_H + 1):
        for cx in range(GRID - BLOCK_W + 1):
            cells = [(cx + c, cy + r) for c, r in SHAPE]
            if any(cell in used for cell in cells):
                continue
            used.update(cells)
            spots.append((cx, cy))
            if len(spots) == count:
                return spots
    return spots


def build_tileset(base_path):
    """Draws every fence block into `base_path`'s empty cells. Returns the
    image and a map of material name to its block's top-left cell."""
    set_ground_source(base_path)
    ts = Image.open(base_path).convert("RGBA")
    defs = fence_defs()
    spots = pack_blocks(ts, len(defs))
    placements = {}
    for fence, (bx, by) in zip(defs, spots):
        draw = STYLE_DRAW[fence["style"]]
        col = COLOURS[fence["colour"]]
        for (c, r), arms in LAYOUT.items():
            ts.paste(padded(draw(arms, col, fence["ground"])), ((bx + c) * CELL, (by + r) * CELL))
        placements[fence["name"]] = (bx, by)
    # A fence that found no room borrows the block of the same style and
    # colour on another ground, so it still exists and still draws.
    for fence in defs[len(spots):]:
        donor = next(f for f in defs[:len(spots)] if f["style"] == fence["style"] and f["colour"] == fence["colour"])
        placements[fence["name"]] = placements[donor["name"]]
        fence["borrowed_from"] = donor["ground"]
    return ts, placements


# ---------------------------------------------------------------- prefab

# The laser cell quick builds: single cells in paired rows either side of a
# corridor, repeated down the block. Every interior wall is a laser fence,
# every cell has a bed, toilet, shower head and a laser door with a drain on
# its tile, and every corridor has a large laser door at each end. The outer
# wall is whatever the player picks when placing the quick build.
PREFABS = [
    # name, label, cells per row, corridors
    ("LaserCellBlock", "Laser Cell Block", 25, 10),
    ("LaserCellWing", "Laser Cell Wing", 5, 2),
]
CELL_W = 2
CELL_H = 3
CORRIDOR_H = 3
UNIT_H = CELL_H + 1 + CORRIDOR_H + 1 + CELL_H + 1
PREFAB_WALL = "LaserFenceRedConcrete"
PREFAB_DOOR = "LaserDoorRed"
PREFAB_EXIT = "LaserDoorLargeRed"


def prefab_text(name, cells_per_row, corridor_units):
    w = 1 + cells_per_row * (CELL_W + 1)
    h = 1 + corridor_units * UNIT_H
    inner_w = w - 2
    trunk_x = 1 + (cells_per_row // 2) * (CELL_W + 1)
    lines = [
        "BEGIN Prefab",
        f"    Name        {name}",
        f"    w           {w}",
        f"    h           {h}",
        "    RoomType    Cell",
    ]

    def material(x, y, mw, mh):
        lines.append(f"    BEGIN Material  Type    {PREFAB_WALL:<22} x {x:3d}  y {y:3d}  w {mw:3d}  h {mh:3d}  END")

    def zone(x, y):
        lines.append(f"    BEGIN Zone      Type    Cell                   x {x:3d}  y {y:3d}  w {CELL_W:3d}  h {CELL_H:3d}  END")

    def obj(kind, x, y, ox=0, oy=1):
        lines.append(f"    BEGIN Object    Type    {kind:<22} x {x:3d}  y {y:3d}  orX {ox:2d}  orY {oy:2d}  END")

    for u in range(corridor_units):
        y0 = 1 + u * UNIT_H
        top = y0                      # first row of the upper cells
        top_wall = y0 + CELL_H        # door wall under the upper cells
        corridor = top_wall + 1       # first corridor row
        mid = corridor + CORRIDOR_H // 2
        bottom_wall = corridor + CORRIDOR_H
        bottom = bottom_wall + 1      # first row of the lower cells
        sep = bottom + CELL_H         # wall row below the lower cells

        material(1, top_wall, inner_w, 1)
        material(1, bottom_wall, inner_w, 1)
        if u < corridor_units - 1:
            material(1, sep, inner_w, 1)
        for k in range(cells_per_row - 1):
            wx = 1 + (k + 1) * (CELL_W + 1) - 1
            material(wx, top, 1, CELL_H)
            material(wx, bottom, 1, CELL_H)

        for k in range(cells_per_row):
            cx = 1 + k * (CELL_W + 1)
            fx = cx + 1               # the fixture column: toilet, shower, door
            # upper cell: door in its south wall
            zone(cx, top)
            obj("Bed", cx, top, 0, 1)
            obj("Toilet", fx, top, 0, 1)
            obj("ShowerHead", fx, top + 1, -1, 0)
            for y in range(top, mid + 1):
                obj("PipeSmall", fx, y)
            obj("Drain", fx, top_wall)
            obj(PREFAB_DOOR, fx, top_wall, 0, 1)
            # lower cell: door in its north wall
            zone(cx, bottom)
            obj("Bed", cx, bottom + 1, 0, 1)
            obj("Toilet", fx, bottom + 2, 0, -1)
            obj("ShowerHead", fx, bottom + 1, -1, 0)
            for y in range(mid, bottom + CELL_H):
                obj("PipeSmall", fx, y)
            obj("Drain", fx, bottom_wall)
            obj(PREFAB_DOOR, fx, bottom_wall, 0, 1)

        for x in range(1, w - 1):
            obj("PipeSmall", x, mid)
        obj(PREFAB_EXIT, 0, corridor, 1, 0)
        obj(PREFAB_EXIT, w - 1, corridor, 1, 0)

    for y in range(1, h - 1):
        obj("PipeSmall", trunk_x, y)
    lines.append("END")
    return "\n".join(lines) + "\n"


def prefabs_text():
    return "\n".join(prefab_text(name, per_row, units) for name, _, per_row, units in PREFABS)


# ---------------------------------------------------------------- text files

def materials_text(placements):
    out = []
    for fence in fence_defs():
        bx, by = placements[fence["name"]]
        out.append(f"""BEGIN Material
    Name                 {fence['name']}
    ConstructionTime     {fence['time']:.4f}
    BlockMovement        true
    MoveCost             0.400000
    SoftEdged            -1
    Price                -{fence['price']}
    SpriteType           Connected
    NumSprites           1
    BEGIN Sprite0    x {bx}  y {by}  END
END
""")
    for door in DOORS:
        name, colour, tiles, price, _ = door
        width = f"    Width                {tiles}\n" if tiles > 1 else ""
        sprites = ""
        for f in range(DOOR_FRAMES):
            sx, sy = door_frame_cell(door, f)
            aligned = "true" if door_frame_top_aligned(f) else "false"
            sprites += f"    BEGIN Sprite         x {sx}  y {sy}  w {door_frame_cells(door, f)}  h 2  RotateType 1  TopAligned {aligned}  END\n"
        out.append(f"""BEGIN Object
    Name                 {name}
{width}    ConstructionTime     15.00000
    Toughness            300.000
    Teleportable         true
    Price                -{price}
    RenderDepth          2
    Group                StaticObject
    BlockedBy            StaticObject
    BlockedBy            UtilityStation
    MadeOf               SolidMetal
    Properties           StaticObject
    Properties           Door
    Properties           Scripted
    NumSprites           {DOOR_FRAMES}
{sprites}END
""")
    panel_sprites = "".join(
        f"    BEGIN Sprite         x {PANEL_X0 + PANEL_STRIDE * f}  y {PANEL_BAND}  w 2  h 2  RotateType 1  TopAligned false  END\n"
        for f in range(PANEL_FRAMES))
    out.append(f"""BEGIN Object
    Name                 LaserDoorPanel
    Width                1
    Height               1
    ConstructionTime     10.0000
    Toughness            50.0000
    Price                -400
    Filter               Security
    AttachToWall         false
    Group                StaticObject
    BlockedBy            Wall
    BlockedBy            StaticObject
    BlockedBy            UtilityStation
    MadeOf               Composite
    Properties           StaticObject
    Properties           Scripted
    NumSprites           {PANEL_FRAMES}
{panel_sprites}END
""")
    controller_sprites = "".join(
        f"    BEGIN Sprite         x {PANEL_X0 + CONTROLLER_X0 + 2 * f}  y {PANEL_BAND}  w 2  h 2  RotateType 0  TopAligned false  END\n"
        for f in range(CONTROLLER_FRAMES))
    out.append(f"""BEGIN Object
    Name                 AILaserController
    Width                1
    Height               1
    ConstructionTime     20.0000
    Toughness            100.000
    Price                -5000
    Filter               Security
    AttachToWall         false
    Group                StaticObject
    BlockedBy            Wall
    BlockedBy            StaticObject
    BlockedBy            UtilityStation
    MadeOf               SolidMetal
    Properties           StaticObject
    Properties           Scripted
    NumSprites           {CONTROLLER_FRAMES}
    BEGIN ToolbarSprite  x {PANEL_X0 + CONTROLLER_X0}  y {PANEL_BAND}  w 2  h 2  END
{controller_sprites}END
""")
    # Like the game's Door Servo it names no group and is blocked by nothing,
    # which is what lets it be built on a door. It draws above the servo.
    out.append(f"""BEGIN Object
    Name                 LaserDoorWireBox
    Width                1
    Height               1
    ConstructionTime     10.0000
    Toughness            100.000
    Price                -200
    Filter               Security
    RenderDepth          4
    AttachToWall         false
    MadeOf               Composite
    Properties           StaticObject
    Properties           Scripted
    Research             RemoteAccess
    NumSprites           1
    BEGIN ToolbarSprite  x {PANEL_X0 + WIRE_BOX_X0}  y {PANEL_BAND}  w 2  h 2  END
    BEGIN Sprite         x {PANEL_X0 + WIRE_BOX_X0}  y {PANEL_BAND}  w 2  h 2  RotateType 0  TopAligned false  END
END
""")
    return "\n".join(out)


def jobs_text():
    """The door's own job: a guard stands at the door for a few seconds to
    pass a meal through it. The door's script raises it and is told when it
    is done."""
    return """BEGIN Job
    Name                 LaserDoorMeal
    JobTime              4
    Worker               Guard
    Worker               ArmedGuard
    Properties           HighPriority
END
"""


def language_text():
    lines = []
    for fence in fence_defs():
        lines.append(f"material_{fence['name']:<34} {fence['label']}")
    door_text = ("A doorway sealed by laser beams. It is a locked door: staff with keys open it and prisoners "
                 "wait to be let through. A guard at a Laser Door Panel within three tiles opens it from there, "
                 "and a triggered Door Servo opens it too.")
    for name, colour, tiles, price, _ in DOORS:
        label = ("Large " if tiles > 1 else "") + f"Laser Door ({colour})"
        lines.append(f"object_{name:<36} {label}")
        lines.append(f"buildtoolbar_popup_obj_{name:<20} {door_text}")
    lines += [
        f"{'object_LaserDoorPanel':<43} Laser Door Panel",
        f"{'buildtoolbar_popup_obj_LaserDoorPanel':<43} Build it within three tiles of a Laser Door. While a guard stands next to the panel, every Laser Door within reach opens, so a guard can let people through without going to the door.",
        f"{'tooltip_LaserDoorPanel_Idle':<43} No guard at the panel.",
        f"{'tooltip_LaserDoorPanel_Active':<43} Guard at the panel. Laser Doors within reach are open.",
        f"{'tooltip_LaserDoor_Shut':<43} Sealed. It opens for any member of staff who walks up to it and never for a prisoner; a guard at a Laser Door Panel or a triggered Door Servo opens it from a distance.",
        f"{'tooltip_LaserDoor_Open':<43} Open.",
        f"{'job_custom_LaserDoorMeal':<43} Pass a meal through the laser door",
        f"{'tooltip_LaserDoor_Auto':<43} Automatic. The AI Laser Controller opens it for whoever is allowed through and shuts it behind them.",
        f"{'tooltip_LaserDoor_Sealed':<43} Sealed against a misbehaving prisoner. Staff with keys can still open it.",
        f"{'object_AILaserController':<43} AI Laser Controller",
        f"{'buildtoolbar_popup_obj_AILaserController':<43} Build one anywhere in the prison and every Laser Door becomes automatic: it opens for staff and for prisoners going about their day and shuts behind them, with no guard needed. A door seals itself the moment a misbehaving prisoner is beside it. One controller runs every door on the map.",
        f"{'tooltip_AILaserController':<43} Running every Laser Door in the prison.",
        f"{'object_LaserDoorWireBox':<43} Laser Door Wire Box",
        f"{'buildtoolbar_popup_obj_LaserDoorWireBox':<43} Build it on a Laser Door to wire the door up. It works as a Door Servo does: use the Connect tool to connect a Door Control System, a pressure pad or a door timer to it, and the door opens when it is triggered. It needs power.",
        f"{'tooltip_LaserDoorWireBox':<43} Wired to the Laser Door it sits on.",
        f"{'tooltip_LaserDoorWireBox_NoServo':<43} Its servo is gone. Build the box again.",
    ]
    for name, label, per_row, units in PREFABS:
        lines.append(f"{'quickbuild_' + name:<43} {label} ({per_row * 2 * units} cells)")
    return "\n".join(lines) + "\n"


def write_text_files(placements, data_dir):
    os.makedirs(os.path.join(data_dir, "language"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "scripts"), exist_ok=True)
    with open(os.path.join(data_dir, "materials.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(materials_text(placements))
    with open(os.path.join(data_dir, "language", "base-language.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(language_text())
    with open(os.path.join(data_dir, "prefabs.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(prefabs_text())
    with open(os.path.join(data_dir, "jobs.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(jobs_text())
    # The game finds an object's script by the object's name, so every door
    # object gets its own copy of the one door script.
    with open(os.path.join(TOOLS, "LaserDoor.lua"), encoding="utf-8") as f:
        door_script = f.read()
    assert "local SETTLE = 0.3\n" in door_script
    for name, _, tiles, _, _ in DOORS:
        script = door_script.replace("local SETTLE = 0.3\n", f"local SETTLE = {SETTLE_SECONDS[tiles]}\n")
        assert "local STAFF_REACH = 1.5 " in script
        script = script.replace("local STAFF_REACH = 1.5 ", f"local STAFF_REACH = {STAFF_REACH[tiles]} ")
        with open(os.path.join(data_dir, "scripts", name + ".lua"), "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
    shutil.copyfile(os.path.join(TOOLS, "LaserDoorPanel.lua"), os.path.join(data_dir, "scripts", "LaserDoorPanel.lua"))
    shutil.copyfile(os.path.join(TOOLS, "AILaserController.lua"),
                    os.path.join(data_dir, "scripts", "AILaserController.lua"))
    shutil.copyfile(os.path.join(TOOLS, "LaserDoorWireBox.lua"),
                    os.path.join(data_dir, "scripts", "LaserDoorWireBox.lua"))


# ---------------------------------------------------------------- output

def build_sprites():
    layout()
    sheet = Image.new("RGBA", (SHEET_CELLS[0] * 32, SHEET_CELLS[1] * 32), (0, 0, 0, 0))
    for door in DOORS:
        _, colour, tiles, _, _ = door
        for f in range(DOOR_FRAMES):
            sx, sy = door_frame_cell(door, f)
            w = door_frame_cells(door, f)
            top = door_frame_vertical_row(door, f)
            flat = door_sprite(COLOURS[colour], tiles, f)
            tall = door_sprite_vertical(COLOURS[colour], tiles, f)
            # the door is symmetric, so both facings share one picture
            sheet.paste(flat, (sx * 32, sy * 32))
            sheet.paste(flat, ((sx + w) * 32, sy * 32))
            sheet.paste(tall, ((sx + 2 * w) * 32, top * 32))
            sheet.paste(tall, ((sx + 2 * w + 2) * 32, top * 32))
    for f in range(PANEL_FRAMES):
        base = panel_sprite(f)
        x0 = PANEL_X0 + PANEL_STRIDE * f
        sheet.paste(base, (x0 * 32, PANEL_BAND * 32))
        sheet.paste(base.transpose(Image.ROTATE_180), ((x0 + 2) * 32, PANEL_BAND * 32))
        sheet.paste(base.transpose(Image.ROTATE_270), ((x0 + 4) * 32, PANEL_BAND * 32))
        sheet.paste(base.transpose(Image.ROTATE_90), ((x0 + 6) * 32, PANEL_BAND * 32))
    for f in range(CONTROLLER_FRAMES):
        sheet.paste(controller_sprite(f), ((PANEL_X0 + CONTROLLER_X0 + 2 * f) * 32, PANEL_BAND * 32))
    sheet.paste(wire_box_sprite(), ((PANEL_X0 + WIRE_BOX_X0) * 32, PANEL_BAND * 32))
    return sheet


def build_thumbnail():
    im = Image.new("RGBA", (256, 256), (16, 18, 21, 255))
    ew = LAYOUT[(1, 0)]
    cells = [
        tile_fence(ew, COLOURS["Red"], "Grass"), tile_grid(ew, COLOURS["Blue"], "Stone"),
        tile_curtain(ew, COLOURS["Red"], "Concrete"), door_sprite(COLOURS["Blue"], 1),
    ]
    for i, t in enumerate(cells):
        im.paste(t.resize((128, 128), Image.NEAREST), ((i % 2) * 128, (i // 2) * 128))
    return im


def build_preview():
    scale = 2
    pitch_x = TILE * scale + 8
    pitch_y = TILE * scale + 22
    rows = [(style, colour) for style in STYLES for colour in COLOURS]
    w = BLOCK_W * pitch_x
    h = len(rows) * BLOCK_H * pitch_y + 3 * 150 + 700
    w = max(w, 1600)
    im = Image.new("RGBA", (w, h), (30, 30, 50, 255))
    d = ImageDraw.Draw(im)
    y0 = 0
    for style, colour in rows:
        for (c, r), arms in LAYOUT.items():
                t = STYLE_DRAW[style](arms, COLOURS[colour], GROUND_ORDER[0]).resize((TILE * scale, TILE * scale), Image.NEAREST)
                x = c * pitch_x
                y = y0 + r * pitch_y + 16
                im.paste(t, (x, y))
                d.text((x, y - 13), f"{style} {colour} c{c} r{r} {arms}", fill=(255, 255, 0, 255))
        y0 += BLOCK_H * pitch_y
    for i, gnd in enumerate(GROUND_ORDER):
        t = tile_fence(LAYOUT[(1, 0)], COLOURS["Red"], gnd).resize((128, 128), Image.NEAREST)
        im.paste(t, (i * 140, y0 + 16))
        d.text((i * 140, y0 + 2), gnd, fill=(255, 255, 0, 255))
    y0 += 150
    x = 0
    for f in (0, OPEN_FRAME_LEFT, OPEN_FRAME_RIGHT, REST_FRAME):
        t = door_sprite(COLOURS["Blue"], 1, f)
        floor = Image.new("RGBA", t.size, (0, 0, 0, 0))
        floor.paste(ground("Concrete"), ((t.size[0] - TILE) // 2, 0))
        floor.alpha_composite(t)
        t = floor.resize((t.size[0] * 2, 128), Image.NEAREST)
        im.paste(t, (x, y0 + 16))
        d.text((x, y0 + 2), f"LaserDoorBlue frame {f}", fill=(255, 255, 0, 255))
        x += t.size[0] + 12
    for label, colour, tiles, f in (("LaserDoorRed vertical", "Red", 1, 0),
                                    ("LaserDoorRed vertical up", "Red", 1, OPEN_FRAME_UP),
                                    ("LaserDoorLargeBlue vertical", "Blue", 2, 0)):
        t = door_sprite_vertical(COLOURS[colour], tiles, f)
        t = t.resize((t.size[0] * 2, t.size[1] * 2), Image.NEAREST)
        im.paste(t, (x, y0 + 16))
        d.text((x, y0 + 2), label, fill=(255, 255, 0, 255))
        x += t.size[0] + 12
    y0 += 150
    for f in range(PANEL_FRAMES):
        im.paste(panel_sprite(f).resize((128, 128), Image.NEAREST), (f * 140, y0 + 16))
        d.text((f * 140, y0 + 2), f"LaserDoorPanel frame {f}", fill=(255, 255, 0, 255))
    return im


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    os.makedirs(DATA, exist_ok=True)
    layout()
    ts, placements = build_tileset(sys.argv[1])
    ts.save(os.path.join(DATA, "tilesetpadded.png"), optimize=True)
    write_text_files(placements, DATA)
    build_sprites().save(os.path.join(DATA, "sprites.png"))
    build_thumbnail().save(os.path.join(ROOT, "tools", "card-art.png"))
    build_preview().save(os.path.join(TOOLS, "preview.png"))
    print(f"wrote {len(placements)} fence materials, {len(DOORS)} doors, tileset {ts.size[0]}x{ts.size[1]}, sprites, thumbnail, preview")


if __name__ == "__main__":
    main()
