-- AI Laser Controller. One of these anywhere on the map runs every Laser
-- Door in the prison: each door looks for a controller for itself, every
-- few seconds, and works automatically for as long as one stands. This
-- script only shows that the controller is alive. Sprites 0 and 1 are the
-- two halves of its status lamp's blink.

local BLINK_INTERVAL = 0.6

local blinkTimer = math.random() * BLINK_INTERVAL
local frame = 0

function Create()
    this.Tooltip = "tooltip_AILaserController"
    this.SubType = 0
end

function Update(timePassed)
    blinkTimer = blinkTimer + timePassed
    if blinkTimer >= BLINK_INTERVAL then
        blinkTimer = 0
        frame = 1 - frame
        this.SubType = frame
    end
end

-- The game hands a script every object a search finds as a global named for
-- the object's type and id, and never takes one back, so a script that
-- searches holds on to everyone it has ever found. Every FORGET_EVERY seconds
-- those globals are cleared, and Lua's own collector frees what they held.
-- Reading a property of an object goes through its global, so this is only
-- for a script that keeps no object from one update to the next.
local FORGET_EVERY = 20
local forgetTimer = math.random() * FORGET_EVERY
local runUpdate = Update
function Update(timePassed)
    forgetTimer = forgetTimer + timePassed
    if forgetTimer >= FORGET_EVERY then
        forgetTimer = 0
        if _G ~= nil then
            for name, value in pairs(_G) do
                if type(value) == "table" and type(name) == "string" and name:find("i%-?%d+u%-?%d+$") then
                    _G[name] = nil
                end
            end
        end
    end
    return runUpdate(timePassed)
end
