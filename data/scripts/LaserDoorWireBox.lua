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

-- Every scripted object is a Lua state of its own, and what a script drops
-- stays in memory until a collection runs. A full one every GC_EVERY seconds
-- keeps a long session from piling it up. The state is small, so it is cheap.
local GC_EVERY = 20
local gcTimer = math.random() * GC_EVERY
local runUpdate = Update
function Update(timePassed)
    gcTimer = gcTimer + timePassed
    if gcTimer >= GC_EVERY then
        gcTimer = 0
        if collectgarbage then collectgarbage("collect") end
    end
    return runUpdate(timePassed)
end
