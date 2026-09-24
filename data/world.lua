-- Sci-Fi Security: the mod's world script. It does the two looks every Laser
-- Door used to make for itself, once for the whole prison.
--
-- A door holds itself open for staff who carry no keys, and it becomes
-- automatic while an AI Laser Controller stands anywhere on the map. Each
-- door used to find out both by searching: for staff at the door a few times
-- a second, and for a controller across the whole map every few seconds. A
-- search is the dearest thing a script can ask the game for, and a big
-- prison holds hundreds of doors, so those looks were nearly all the mod
-- cost. Here one search for a kind of staff covers every door at once, and
-- one search for a controller does too.
--
-- The script tells each door what it found by writing on the door itself:
--   LaserStaff  a number that changes on every round that saw living staff
--               of a kind the door waits for standing at it
--   LaserAuto   1 while a controller stands on the map, and 0 otherwise
--   LaserWorld  a number that changes on every pass over the doors, which is
--               how a door knows this script is running. A door that has not
--               seen it change for a while does its own looks again, as it
--               always did, so nothing depends on this script working.
--
-- One search for a kind of staff hands back every member of that kind on the
-- map, which costs more than a few doors' own looks put together. So the
-- script only takes the looks over once the prison holds TAKE_OVER_AT doors,
-- and below that it writes nothing and every door looks for itself.
--
-- A world script has no object of its own to search from, so every door
-- names itself ANCHOR and a search is made from whichever door the game
-- hands back for that name. The whole map is in reach of any of them.

local Find = Object.GetNearbyObjects
local Set  = Object.SetProperty
local safe = pcall or function(f, ...) return true, f(...) end

local ANCHOR = "LaserDoorUnit"
local DOOR_REACH = { LaserDoorRed = 1.5, LaserDoorBlue = 1.5, LaserDoorLargeRed = 2.0, LaserDoorLargeBlue = 2.0 }
local CONTROLLER = "AILaserController"
local WHOLE_MAP = 5000
local TAKE_OVER_AT = 40   -- doors on the map before this script makes their looks

-- The same kinds, in the same turns, the doors looked for: the kinds a door is
-- likeliest to meet, with one of the kinds it seldom meets every RARE_EVERY
-- rounds, and any kind seen at a door on the last round again on every round
-- until it has gone.
local STAFF_KINDS = { "Workman", "Cook", "Janitor", "Doctor", "Gardener" }
local RARE_STAFF_KINDS = { "Orderly", "Farmer", "Foreman", "Warden", "Chief", "Psychologist", "Psychiatrist",
                           "Accountant", "Lawyer", "Teacher", "SpiritualLeader", "Paramedic", "Fireman" }
local RARE_EVERY = 3

local ROUND = 0.3         -- seconds between looks for staff, as a door's own
local DOORS_EVERY = 5     -- seconds between passes over the doors
local CONTROL_EVERY = 10  -- seconds between looks for a controller, as a door's own

local roundTimer = 0
local doorsTimer = DOORS_EVERY
local controlTimer = CONTROL_EVERY
local rounds = 0
local passes = 0
local commonAt = 0
local rareAt = 0
local hot = {}            -- kind -> true when seen at a door on the last round
local controlled = false
local active = false      -- whether there are doors enough for this script to look for them

-- Every door, by the tile it stands on, and each with its reach. Doors never
-- move, so they are gathered once a pass and kept in between.
local byTile = {}

local function tileKey(x, y)
    return math.floor(x) * 4096 + math.floor(y)
end

local function gatherDoors(anchor)
    passes = passes + 1
    byTile = {}
    local doors = {}
    for kind, reach in pairs(DOOR_REACH) do
        for door in pairs(Find(anchor, kind, WHOLE_MAP) or {}) do
            local pos = door.Pos
            local x, y = pos and tonumber(pos.x), pos and tonumber(pos.y)
            if x ~= nil and y ~= nil then
                local key = tileKey(x, y)
                local list = byTile[key]
                if list == nil then
                    list = {}
                    byTile[key] = list
                end
                local entry = { door = door, x = x, y = y, reach = reach }
                list[#list + 1] = entry
                doors[#doors + 1] = entry
            end
        end
    end
    active = #doors >= TAKE_OVER_AT
    if not active then
        byTile = {}
        return
    end
    for _, entry in ipairs(doors) do
        safe(Set, entry.door, "LaserAuto", controlled and 1 or 0)
        safe(Set, entry.door, "LaserWorld", passes)
    end
end

-- Stamps every door within its reach of one member of staff. Returns whether
-- any door was.
local function stampAround(x, y)
    local any = false
    local tx, ty = math.floor(x), math.floor(y)
    for dx = -3, 3 do
        for dy = -3, 3 do
            local list = byTile[tileKey(tx + dx, ty + dy)]
            if list ~= nil then
                for _, entry in ipairs(list) do
                    local ex, ey = entry.x - x, entry.y - y
                    if ex * ex + ey * ey <= entry.reach * entry.reach then
                        -- a door taken down since the last pass is simply skipped
                        safe(Set, entry.door, "LaserStaff", rounds)
                        any = true
                    end
                end
            end
        end
    end
    return any
end

local function lookFor(anchor, kind, seen)
    for member in pairs(Find(anchor, kind, WHOLE_MAP) or {}) do
        if (tonumber(member.Damage) or 0) < 1 then
            local pos = member.Pos
            local x, y = pos and tonumber(pos.x), pos and tonumber(pos.y)
            if x ~= nil and y ~= nil and stampAround(x, y) then
                seen[kind] = true
            end
        end
    end
end

local function staffRound(anchor)
    rounds = rounds + 1
    local kind
    if rounds % RARE_EVERY == 0 then
        rareAt = rareAt % #RARE_STAFF_KINDS + 1
        kind = RARE_STAFF_KINDS[rareAt]
    else
        commonAt = commonAt % #STAFF_KINDS + 1
        kind = STAFF_KINDS[commonAt]
    end
    local seen = {}
    for each in pairs(hot) do
        if each ~= kind then lookFor(anchor, each, seen) end
    end
    lookFor(anchor, kind, seen)
    hot = seen
end

function Init()
end

function Update(timePassed)
    local dt = tonumber(timePassed) or 0
    roundTimer = roundTimer + dt
    doorsTimer = doorsTimer + dt
    controlTimer = controlTimer + dt
    if roundTimer < ROUND then
        return
    end
    roundTimer = 0
    local anchor = Game.GetObject(ANCHOR)
    if anchor == nil then
        byTile = {}
        return
    end
    if controlTimer >= CONTROL_EVERY then
        controlTimer = 0
        local found = next(Find(anchor, CONTROLLER, WHOLE_MAP) or {}) ~= nil
        if found ~= controlled then
            controlled = found
            doorsTimer = DOORS_EVERY    -- tell every door now
        end
    end
    if doorsTimer >= DOORS_EVERY then
        doorsTimer = 0
        gatherDoors(anchor)
    end
    if active then
        staffRound(anchor)
    end
end

-- The game hands a script every object a search finds as a global named for
-- the object's type and id, and never takes one back, so a script that
-- searches holds on to everyone it has ever found. Every FORGET_EVERY seconds
-- those globals are cleared, and Lua's own collector frees what they held.
-- Reading a property of an object goes through its global, so the doors this
-- script keeps between passes keep theirs.
local FORGET_EVERY = 20
local forgetTimer = math.random() * FORGET_EVERY
local runUpdate = Update
function Update(timePassed)
    forgetTimer = forgetTimer + (tonumber(timePassed) or 0)
    if forgetTimer >= FORGET_EVERY then
        forgetTimer = 0
        if _G ~= nil then
            for name, value in pairs(_G) do
                if type(value) == "table" and type(name) == "string" and name:find("i%-?%d+u%-?%d+$")
                    and not name:find("^LaserDoor") then
                    _G[name] = nil
                end
            end
        end
    end
    return runUpdate(timePassed)
end
