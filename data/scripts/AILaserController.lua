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
