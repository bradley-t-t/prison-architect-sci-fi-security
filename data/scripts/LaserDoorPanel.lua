-- Laser Door Panel. The panel watches for a guard standing at it and shows
-- it: sprite 0 is the idle console, and sprites 1 and 2 alternate to blink
-- the status lamp while a guard is there. Each Laser Door within reach reads
-- that lamp rather than looking for guards itself, so the lamp is the signal
-- as well as the display.

local SCAN_INTERVAL = 0.25
local GUARD_REACH = 1.6
local BLINK_INTERVAL = 0.4

local GUARDS = { "Guard", "ArmedGuard", "RiotGuard", "Sniper", "DogHandler" }

local scanTimer = math.random() * SCAN_INTERVAL
local blinkTimer = 0
local guardHere = false
local frame = -1

local function showFrame(n)
    if frame ~= n then
        frame = n
        this.SubType = n
    end
end

local function guardNearby()
    for _, kind in ipairs(GUARDS) do
        for _ in pairs(Object.GetNearbyObjects(kind, GUARD_REACH) or {}) do
            return true
        end
    end
    return false
end

function Create()
    this.Tooltip = "tooltip_LaserDoorPanel_Idle"
    showFrame(0)
end

function Update(timePassed)
    scanTimer = scanTimer + timePassed
    if scanTimer >= SCAN_INTERVAL then
        scanTimer = 0
        local here = guardNearby()
        if here ~= guardHere then
            guardHere = here
            this.Tooltip = here and "tooltip_LaserDoorPanel_Active" or "tooltip_LaserDoorPanel_Idle"
        end
    end

    if guardHere then
        blinkTimer = blinkTimer + timePassed
        if frame < 1 or blinkTimer >= BLINK_INTERVAL then
            blinkTimer = 0
            showFrame(frame == 1 and 2 or 1)
        end
    else
        blinkTimer = 0
        showFrame(0)
    end
end
