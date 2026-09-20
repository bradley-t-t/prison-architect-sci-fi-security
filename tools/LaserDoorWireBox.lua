-- The Laser Door Wire Box is how a Laser Door is wired up. A Door Control
-- System, a pressure pad or a door timer can only be connected to the game's
-- own Door Servo, so the box brings one in underneath itself and sits on top
-- of it. The servo does the work, the door reads the servo, and the box is
-- what you see.
--
-- A box brings in one servo in its life and records that it has, so a servo
-- the search cannot see is never answered with another every few seconds.
--
-- A script is not told when its object is dismantled, so a box that is taken
-- away uncovers its servo, which is then dismantled like any other.

local Find = Object.GetNearbyObjects
local Spawn = Object.Spawn

local UNDER = 0.4               -- a servo this close is the one under the box
local CHECK_EVERY = 5           -- seconds between looks for the servo

local checkTimer = CHECK_EVERY  -- look on the first update

local function servoUnder()
    for servo in pairs(Find("Servo", UNDER) or {}) do
        return servo
    end
    return nil
end

function Update(timePassed)
    checkTimer = checkTimer + (tonumber(timePassed) or 0)
    if checkTimer < CHECK_EVERY then
        return
    end
    checkTimer = CHECK_EVERY * 0.25 * math.random()
    if servoUnder() then
        this.Tooltip = "tooltip_LaserDoorWireBox"
    elseif this.ServoMade then
        this.Tooltip = "tooltip_LaserDoorWireBox_NoServo"
    else
        Object.SetProperty("ServoMade", true)
        if not Spawn("Servo", this.Pos.x, this.Pos.y) then
            this.Tooltip = "tooltip_LaserDoorWireBox_NoServo"
        end
    end
end

-- The game hands a script every object a search finds as a global named for
-- the object's type and id, and never takes one back, so a script that
-- searches holds on to everyone it has ever found. Every FORGET_EVERY seconds
-- those globals are cleared, and Lua's own collector frees what they held.
-- Objects the script still has in a local stay usable.
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
