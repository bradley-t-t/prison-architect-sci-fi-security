-- Laser Door. The engine runs the door like a locked jail door: it asks the
-- game to lock it, and the game then opens it for staff with keys and their
-- escorts and makes prisoners wait, exactly as it does for its own doors. On
-- top of that the script opens it from a distance while a guard stands at a
-- Laser Door Panel within reach or a Door Servo on the door is triggered.
--
-- The engine draws a door at its position plus OpenDir times its openness,
-- which is how its own doors slide into the wall. A laser door's frame must
-- not move, so the script holds OpenDir at zero and the sprite stays in the
-- doorway whatever the door is doing. Sprites 0 to 2 are the sealed door with
-- its beams pulsing, and sprite 8 is the same frame with its beams off, shown
-- while the door is open or broken.
--
-- The script still never lets the door sit part-way: the tick the engine
-- starts opening it, the script snaps it fully open, and the tick it starts
-- closing, fully shut, so the beams cut out and come back at once.
--
-- If OpenDir cannot be held at zero the script falls back to the pre-shifted
-- frames. Sprites 3 and 4 hold the beamless frame one slide to the left or
-- right and sprites 6 and 7 one slide down or up; the script shows the one
-- drawn opposite the slide, so the engine's offset carries it back into the
-- doorway. OpenDir is the door's facing turned a quarter turn, times its
-- width, so which one that is depends on how the door was rotated. Sprite 5
-- is empty: it covers the ticks where the door is part-way and the settle
-- time after each change of state, while the renderer catches up.
--
-- The beams bite back. Any tick the door takes damage, whoever is standing
-- against it is tazed the way a guard's tazer would drop them, and the door's
-- own damage is wiped the same tick. So it can never be broken open, and a
-- prisoner who swings at it is put on the floor rather than through it.

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
local REST_FRAME = 8
-- The engine treats an object as broken from this much damage.
local BROKEN_AT = 0.7
local SHUT = 0.02
local OPENED = 0.98
-- Set per door by the build: the single door needs it, the large door does not.
local SETTLE = 0.3
-- The stun a hit earns: how far from the door a prisoner counts as touching it,
-- and how long the taze lasts. 60 is a guard tazer's full charge.
local ZAP_REACH = 1.5
local STUN = 60
local DAMAGE_EPSILON = 0.001

local GUARDS = { "Guard", "ArmedGuard", "RiotGuard", "Sniper", "DogHandler" }

local remoteOpen = false
local scanTimer = SCAN_INTERVAL
local pulseTimer = 0
local settleTimer = 0
local frame = -1
local lastRaw = 0
local wasOpen = false
local lastDamage = 0

local function showFrame(n)
    if frame ~= n then
        frame = n
        this.SubType = n
    end
end

local function nearby(kind, range)
    return Object.GetNearbyObjects(kind, range) or {}
end

local function shockAttackers()
    -- Damage only rises when something is hitting the door. When it does, taze
    -- every prisoner against the door, then wipe the damage so it never breaks.
    local dmg = tonumber(this.Damage) or 0
    if dmg > lastDamage + DAMAGE_EPSILON then
        for prisoner, _ in pairs(nearby("Prisoner", ZAP_REACH)) do
            if prisoner ~= nil and prisoner.StatusEffects ~= nil then
                prisoner.StatusEffects.tazed = STUN
            end
        end
    end
    if dmg > 0 then
        this.Damage = 0
    end
    lastDamage = 0
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

local function holdStill()
    -- True once the engine has no slide left to apply to this door.
    local dir = this.OpenDir
    if dir == nil then
        return false
    end
    local x, y = tonumber(dir.x), tonumber(dir.y)
    if x == nil or y == nil then
        return false
    end
    if x ~= 0 then
        dir.x = 0
    end
    if y ~= 0 then
        dir.y = 0
    end
    return tonumber(dir.x) == 0 and tonumber(dir.y) == 0
end

local function slideDirection()
    local dir = this.OpenDir
    if dir ~= nil then
        local x, y = tonumber(dir.x), tonumber(dir.y)
        if x ~= nil and y ~= nil then
            return x, y
        end
    end
    -- The engine's own sum: the facing turned a quarter turn. A door that
    -- was never rotated faces south.
    local facingX, facingY = 0, 1
    if this.Or ~= nil then
        facingX = tonumber(this.Or.x) or 0
        facingY = tonumber(this.Or.y) or 0
    end
    return -facingY, facingX
end

local function openFrame()
    -- Only reached when the slide could not be switched off: the frame drawn
    -- on the side the door slides away from is the one that lands in the
    -- doorway.
    local x, y = slideDirection()
    if y < 0 then
        return OPEN_FRAME_DOWN
    end
    if y > 0 then
        return OPEN_FRAME_UP
    end
    if x > 0 then
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
    shockAttackers()

    local still = holdStill()

    if isBroken() then
        -- The engine holds a broken door open, so without the hold it is
        -- slid like any other open door.
        if still or (tonumber(this.Open) or 0) < OPENED then
            showFrame(REST_FRAME)
        else
            showFrame(openFrame())
        end
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

    local partWay = raw > SHUT and raw < OPENED
    if still and (isOpen or partWay) then
        showFrame(REST_FRAME)
        pulseTimer = 0
    elseif not still and (partWay or settleTimer > 0) then
        showFrame(TRANSITION_FRAME)
        pulseTimer = 0
    elseif not still and isOpen then
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
