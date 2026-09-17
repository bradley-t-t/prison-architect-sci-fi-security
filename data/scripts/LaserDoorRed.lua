-- Laser Door. The engine runs the door like a locked jail door: it asks the
-- game to lock it, and the game then opens it for staff with keys and their
-- escorts and makes prisoners wait, exactly as it does for its own doors. On
-- top of that the script opens it from a distance while a guard stands at a
-- Laser Door Panel within reach or a Door Servo on the door is triggered.
--
-- The engine slides a door's sprite along the wall as its openness rises,
-- so the script never lets the door sit part-way: the tick the engine starts
-- opening it, the script snaps it fully open, and the tick it starts closing,
-- fully shut. Sprites 0 to 2 are the sealed door with its beams pulsing.
-- Sprites 3 and 4 hold the beamless frame drawn one slide to the left or
-- right; the engine's offset carries it back into the doorway, so an open
-- door looks like the beams simply switched off. A door standing in a
-- north-south wall uses sprites 6 and 7 instead, shifted down or up. Sprite
-- 5 is empty: it is shown on any tick that still reports the door part-way
-- open, and for a short settle time after each change of state, which
-- covers the renderer catching up with a change made within one update.
-- Sprite 8 is the frame at rest with its beams off, shown while the door is
-- broken: the engine draws a broken door without its slide, so a shifted
-- open frame would sit beside the doorway.

local SCAN_INTERVAL = 0.2
local PANEL_REACH = 3.5
local PANEL_GUARD_REACH = 1.6
local SERVO_REACH = 1.0
local PULSE_INTERVAL = 0.12
local PULSE_FRAMES = 3
local OPEN_FRAME_LEFT = 3
local OPEN_FRAME_RIGHT = 4
local TRANSITION_FRAME = 5
local OPEN_FRAME_DOWN = 6
local OPEN_FRAME_UP = 7
local BROKEN_FRAME = 8
local BROKEN_AT = 0.999
local SHUT = 0.02
local OPENED = 0.98
-- Set per door by the build: the single door needs it, the large door does not.
local SETTLE = 0.3

local GUARDS = { "Guard", "ArmedGuard", "RiotGuard", "Sniper", "DogHandler" }

local remoteOpen = false
local scanTimer = SCAN_INTERVAL
local pulseTimer = 0
local settleTimer = 0
local frame = -1
local lastRaw = 0
local wasOpen = false

local function showFrame(n)
    if frame ~= n then
        frame = n
        this.SubType = n
    end
end

local function nearby(kind, range)
    return Object.GetNearbyObjects(kind, range) or {}
end

local function servoWantsOpen()
    for servo, _ in pairs(nearby("Servo", SERVO_REACH)) do
        if servo ~= nil and servo.Triggered ~= nil then
            local triggered = (tonumber(servo.Triggered) or 0) > 0
            if not servo.OpenOnTrigger then
                triggered = not triggered
            end
            if triggered then
                return true
            end
        end
    end
    return false
end

local function guardAtPanel()
    local panels = nearby("LaserDoorPanel", PANEL_REACH)
    if next(panels) == nil then
        return false
    end
    for _, kind in ipairs(GUARDS) do
        for guard, _ in pairs(nearby(kind, PANEL_REACH + PANEL_GUARD_REACH)) do
            for panel, _ in pairs(panels) do
                if guard ~= nil and panel ~= nil and guard.Pos ~= nil and panel.Pos ~= nil
                    and math.abs(guard.Pos.x - panel.Pos.x) <= PANEL_GUARD_REACH
                    and math.abs(guard.Pos.y - panel.Pos.y) <= PANEL_GUARD_REACH then
                    return true
                end
            end
        end
    end
    return false
end

local function openFrame()
    -- The engine slides the sprite in the door's open direction; the frame
    -- drawn on the opposite side lands in the doorway. A door standing in a
    -- north-south wall (facing east or west) has its own pair of frames.
    local dir = tonumber(this.OpenDir) or 0
    local vertical = this.Or ~= nil and (tonumber(this.Or.x) or 0) ~= 0
    if vertical then
        if dir > 0 then
            return OPEN_FRAME_DOWN
        end
        return OPEN_FRAME_UP
    end
    if dir > 0 then
        return OPEN_FRAME_LEFT
    end
    return OPEN_FRAME_RIGHT
end

function Create()
    this.Locked = true
    this.Tooltip = "tooltip_LaserDoor_Shut"
    showFrame(0)
end

local function isBroken()
    return (tonumber(this.Damage) or 0) >= BROKEN_AT
end

function Update(timePassed)
    if isBroken() then
        showFrame(BROKEN_FRAME)
        pulseTimer = 0
        settleTimer = 0
        return
    end

    scanTimer = scanTimer + timePassed
    if scanTimer >= SCAN_INTERVAL then
        scanTimer = 0
        local open = servoWantsOpen() or guardAtPanel()
        if open ~= remoteOpen then
            remoteOpen = open
            this.Tooltip = remoteOpen and "tooltip_LaserDoor_Open" or "tooltip_LaserDoor_Shut"
        end
    end

    local raw = tonumber(this.Open) or 0
    local openness = raw
    if remoteOpen then
        openness = 1
    elseif raw > SHUT and raw < OPENED then
        -- part-way: the engine is animating. Snap in the direction it is going.
        if raw >= lastRaw then
            openness = 1
        else
            openness = 0
        end
    end
    lastRaw = raw
    if openness ~= raw then
        this.Open = openness
    end

    local isOpen = openness >= OPENED
    if isOpen ~= wasOpen then
        wasOpen = isOpen
        settleTimer = SETTLE
    end
    if settleTimer > 0 then
        settleTimer = settleTimer - timePassed
    end

    if (raw > SHUT and raw < OPENED) or settleTimer > 0 then
        showFrame(TRANSITION_FRAME)
        pulseTimer = 0
    elseif isOpen then
        showFrame(openFrame())
        pulseTimer = 0
    else
        pulseTimer = pulseTimer + timePassed
        if frame >= PULSE_FRAMES then
            showFrame(0)
        elseif pulseTimer >= PULSE_INTERVAL then
            pulseTimer = 0
            showFrame((frame + 1) % PULSE_FRAMES)
        end
    end
end
