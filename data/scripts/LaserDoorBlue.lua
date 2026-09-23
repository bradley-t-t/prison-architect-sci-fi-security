-- Laser Door. The engine runs the door like a locked jail door: it asks the
-- game to lock it, and the game then opens it for staff with keys and their
-- escorts and makes prisoners wait, exactly as it does for its own doors. On
-- top of that the script opens it from a distance while a guard stands at a
-- Laser Door Panel within reach or a Door Servo on the door is triggered.
--
-- The door also opens itself for staff. The game opens a locked door only for
-- whoever carries keys, so a cook or a workman waits at it for a guard. The
-- script looks for staff standing at the door a few times a second and holds
-- it open while one is there. It looks for staff and never for prisoners, so
-- a prisoner standing at the door opens nothing. An automatic door that is
-- not sealed is unlocked, and the game opens it for staff itself, so it does
-- not look for them.
--
-- An AI Laser Controller anywhere on the map makes the door automatic. The
-- script then asks the game to unlock it, and the game opens and shuts it
-- for whoever walks up, staff and prisoners alike, by its own rules for an
-- unlocked door: it opens for someone whose route goes through it and shuts
-- behind them, and the game only routes people where they are allowed to
-- go. The controller is not a fool, though. The moment the door starts to
-- open, and for as long as it stands open, it looks at the prisoners beside
-- it, and if one of them is misbehaving (fighting, rioting, escaping) it
-- slams shut and goes back to being a locked door for a few seconds, which
-- staff with keys can still open. With no controller on the map the door is
-- the locked door it always was.
--
-- Meals come to the door during a bangup, and only then. The game feeds a
-- prisoner in his cell only while he is on a lockdown or solitary punishment,
-- and those meals stay the game's: its guard brings them as he would through
-- any door. A bangup holds everyone else in their cells with no meal coming
-- at all, so that is when a laser door on a cell feeds its own prisoners.
--
-- A script cannot read whether a bangup is on. What it can read is what a
-- bangup does and no hour of a regime does: a prisoner at home, on no
-- punishment, hungry, who last ate longer ago than a night lasts. Once a
-- minute the door looks at the prisoners of its cell, and for one like that
-- it raises a job of its own, LaserDoorMeal, which a guard works standing at
-- the door. When that job is done the door feeds every such prisoner of the
-- cell, and the guard never goes inside. A door that is not on a cell reads
-- one property and does none of it.
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
-- If OpenDir cannot be held at zero the script asks for frames 3 to 7, which
-- were once the beamless frame drawn a slide to either side, so the engine's
-- offset carried it back into the doorway. Every door in a played prison held
-- its slide at zero and those pictures were most of the mod's sprite sheet, so
-- all five now show the rest frame: a door that cannot hold its slide shows
-- its posts a little off the doorway while it is open.
--
-- The beams bite back. Any tick the door takes damage, whoever is standing
-- against it is tazed the way a guard's tazer would drop them, and the door's
-- own damage is wiped the same tick. So it can never be broken open, and a
-- prisoner who swings at it is put on the floor rather than through it.
--
-- Every read of a property on this is a call into the engine, and a prison
-- can hold hundreds of these doors each updated every tick, so the script
-- does as little as it can, three ways:
--   It works in steps of STEP seconds. A tick inside a step adds up the time
--   and returns, so at sixty frames a second five ticks in six cost nothing.
--   A step that changes nothing reads the damage and the openness only.
--   Looking around the door for servos and panels is a search of the map,
--   the dearest thing a script can ask for. Neither ever moves, so they are
--   looked for once every FIND_EVERY seconds and remembered, and between
--   looks the door reads the remembered servo's trigger and the remembered
--   panel's own light, which the panel's script sets while a guard stands at
--   it. A door with neither, which is nearly all of them, reads nothing.
--   The controller is looked for once every CONTROL_FIND_EVERY seconds, and
--   prisoners are looked at only while the door is opening or open, which
--   for nearly every door is nearly never.
--   Each door starts its timers at a random point, so hundreds of doors
--   built together do not all look around on the same tick.

local STEP = 0.1
local SCAN_INTERVAL = 0.2
local FIND_EVERY = 8
local CONTROLLER = "AILaserController"
local CONTROL_FIND_EVERY = 10
local CONTROL_REACH = 5000   -- tiles; wider than any map
-- How near a misbehaving prisoner seals an automatic door, and for how long
-- it stays an ordinary locked door afterwards.
local THREAT_REACH = 3

-- Staff at the door. The game opens a locked door for anyone carrying keys,
-- so the door looks only for the staff who carry none. A search is a call
-- into the engine whatever it finds, and a prison holds hundreds of doors, so
-- a look asks for one kind of person and the kinds take turns: the kinds a
-- door is likeliest to meet, with one of the kinds it seldom meets every
-- RARE_EVERY looks. Staff without keys stand at a locked door and wait, so
-- the door finds them within a few looks. Once it has, it asks for that kind
-- alone until they have gone.
local STAFF_KINDS = { "Workman", "Cook", "Janitor", "Doctor", "Gardener" }
local RARE_STAFF_KINDS = { "Orderly", "Farmer", "Foreman", "Warden", "Chief", "Psychologist", "Psychiatrist",
                           "Accountant", "Lawyer", "Teacher", "SpiritualLeader", "Paramedic", "Fireman" }
local RARE_EVERY = 3
local STAFF_REACH = 1.5         -- tiles from the door's middle
local STAFF_EVERY = 0.3         -- seconds between looks
local STAFF_RELOOK = 1.0        -- seconds to the next look once staff have been seen
local STAFF_HOLD = 1.6          -- seconds the door stays open after staff were last seen at it
local THREAT_EVERY = 0.6        -- seconds between looks for trouble while the door is open
local LOCKOUT = 4
-- The engine shuts a door it opened itself and no other. A door found standing
-- open with nothing of the script's holding it is shut after this long; if the
-- engine has someone in the doorway it opens again at once.
local STUCK_AFTER = 10
local PANEL_REACH = 3.5
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
local ZAP_EVERY = 1.5           -- seconds between two shocks from one door
-- The engine works out OpenDir once, when it initialises the door, and never
-- again. Once it has been seen at zero it is only looked at this often.
local HOLD_RECHECK = 0.5

-- Meals at the door: how often a cell's door looks at its prisoners, how far
-- into the cell it looks, the hunger (0 to 100) and the game minutes since a
-- prisoner's last meal at which it calls a guard, how long it waits for one
-- before asking again, and how long after a meal it will not ask at all when
-- hunger cannot be read. UNFED_FOR is the game's own measure of a prisoner
-- overdue a meal, sixteen hours, which no night between two meals reaches.
--
-- A search for prisoners is the dearest thing a door does: the game builds a
-- full script record of every prisoner it hands back, afresh every time, and
-- measured in a prison of a hundred cells those searches were half of all the
-- time the game spent. So a door looks into its cell once a minute, and only
-- as far as a cell is deep.
local MEAL_JOB = "LaserDoorMeal"
local MEAL_CHECK_EVERY = 60
local CELL_REACH = 4
local FOOD_AT = 45
local UNFED_FOR = 960
local MEAL_GIVE_UP = 180
local MEAL_GAP = 480

local remoteOpen = false
local stepTimer = math.random() * STEP
local scanTimer = math.random() * SCAN_INTERVAL
-- The servos and panels last found by the door, and when to look again. The
-- first look is on the first step.
local servos = {}
local panels = {}
local findTimer = FIND_EVERY
local findAfter = FIND_EVERY
-- Whether a controller stands on the map, when to look again, and how long
-- the door has left as a locked door after sealing against someone.
local controlled = false
local controlTimer = CONTROL_FIND_EVERY
local controlAfter = CONTROL_FIND_EVERY
local lockout = 0
local threatTimer = 0
-- The meal job: whether one is out, how long it has been, and when this
-- door last fed anyone.
local mealTimer = math.random() * MEAL_CHECK_EVERY
local staffTimer = math.random() * STAFF_EVERY
local staffHold = 0
local staffLooks = 0
local staffKind = nil           -- the kind of staff last seen at the door
local commonAt = 0
local rareAt = 0
local forced = false            -- the script, not the engine, has the door open
local openFor = 0
local mealOut = false
local mealWait = 0
local clock = 0
local lastMeal = -MEAL_GAP
-- When the door first saw each prisoner who has never eaten, in game minutes.
local firstSeen = {}
local pulseTimer = 0
local settleTimer = 0
local frame = -1
local lastRaw = 0
local wasOpen = false
local lastDamage = 0
local zapWait = 0
local held = false
local holdTimer = 0

local function showFrame(n)
    if frame ~= n then
        frame = n
        this.SubType = n
    end
end

local function nearby(kind, range)
    return Object.GetNearbyObjects(kind, range) or {}
end

local function shockAttackers(timePassed)
    -- Damage only rises when something is hitting the door. When it does, taze
    -- every prisoner against the door, then wipe the damage so it never breaks.
    -- Returns the damage the door is left with, read back only after a wipe.
    -- A door under attack is damaged on every step, and a search for the
    -- prisoners at it on every one of those was, measured, the dearest thing
    -- the doors of a rioting prison did. Whoever a shock drops stays down for
    -- a minute, so one shock every ZAP_EVERY loses nothing; the damage is
    -- still wiped on every step.
    local dmg = tonumber(this.Damage) or 0
    if zapWait > 0 then
        zapWait = zapWait - timePassed
    end
    if dmg > lastDamage + DAMAGE_EPSILON and zapWait <= 0 then
        zapWait = ZAP_EVERY
        for prisoner, _ in pairs(nearby("Prisoner", ZAP_REACH)) do
            if prisoner ~= nil and prisoner.StatusEffects ~= nil then
                prisoner.StatusEffects.tazed = STUN
            end
        end
    end
    lastDamage = 0
    if dmg > 0 then
        this.Damage = 0
        return tonumber(this.Damage) or 0
    end
    return dmg
end

local function lookAround()
    servos, panels = {}, {}
    for servo, _ in pairs(nearby("Servo", SERVO_REACH)) do
        servos[#servos + 1] = servo
    end
    for panel, _ in pairs(nearby("LaserDoorPanel", PANEL_REACH)) do
        panels[#panels + 1] = panel
    end
    -- the next look is a little early or late, so doors drift apart
    findAfter = FIND_EVERY * (0.75 + 0.5 * math.random())
end

local function servoWantsOpen()
    for _, servo in ipairs(servos) do
        local state = servo.Triggered
        if state ~= nil then
            local triggered = (tonumber(state) or 0) > 0
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

-- A panel shows frame 1 or 2 for as long as a guard stands at it.
local function guardAtPanel()
    for _, panel in ipairs(panels) do
        if (tonumber(panel.SubType) or 0) >= 1 then
            return true
        end
    end
    return false
end

-- True while a living member of staff stands at the door. A body at a door
-- holds nothing open.
local function someoneOf(kind)
    for member in pairs(nearby(kind, STAFF_REACH)) do
        if (tonumber(member.Damage) or 0) < 1 then
            return true
        end
    end
    return false
end

local function staffAtDoor()
    if staffKind ~= nil then
        if someoneOf(staffKind) then
            return true
        end
        staffKind = nil
    end
    staffLooks = staffLooks + 1
    local kind
    if staffLooks % RARE_EVERY == 0 then
        rareAt = rareAt % #RARE_STAFF_KINDS + 1
        kind = RARE_STAFF_KINDS[rareAt]
    else
        commonAt = commonAt % #STAFF_KINDS + 1
        kind = STAFF_KINDS[commonAt]
    end
    if someoneOf(kind) then
        staffKind = kind
        return true
    end
    return false
end

local function showTooltip()
    if remoteOpen then
        this.Tooltip = "tooltip_LaserDoor_Open"
    elseif controlled then
        this.Tooltip = lockout > 0 and "tooltip_LaserDoor_Sealed" or "tooltip_LaserDoor_Auto"
    else
        this.Tooltip = "tooltip_LaserDoor_Shut"
    end
end

local function lookForController()
    local found = next(nearby(CONTROLLER, CONTROL_REACH)) ~= nil
    controlAfter = CONTROL_FIND_EVERY * (0.75 + 0.5 * math.random())
    if found ~= controlled then
        controlled = found
        lockout = 0
        this.Locked = not controlled
        showTooltip()
    end
end

-- The game keeps a prisoner's misbehaviour as a name or a number, and
-- either way nothing, zero and "None" are a prisoner behaving.
local function misbehaving(prisoner)
    local what = prisoner.Misbehavior
    if what == nil or what == "" or what == "None" then
        return false
    end
    local n = tonumber(what)
    return n == nil or n ~= 0
end

local function threatAtDoor()
    for prisoner, _ in pairs(nearby("Prisoner", THREAT_REACH)) do
        if prisoner ~= nil and misbehaving(prisoner) then
            return true
        end
    end
    return false
end

-- Runs the automatic door's guard against trouble. Returns true on the step
-- it seals the door.
local function watchForTrouble(timePassed, raw)
    if lockout > 0 then
        lockout = lockout - timePassed
        if lockout <= 0 then
            if threatAtDoor() then
                lockout = LOCKOUT
            else
                lockout = 0
                this.Locked = false
                showTooltip()
            end
        end
        return false
    end
    if raw <= SHUT then
        threatTimer = THREAT_EVERY    -- look the moment it next starts to open
        return false
    end
    threatTimer = threatTimer + timePassed
    if threatTimer < THREAT_EVERY then
        return false
    end
    threatTimer = 0
    if not threatAtDoor() then
        return false
    end
    lockout = LOCKOUT
    this.Locked = true
    this.Open = 0
    showTooltip()
    return true
end

-- Game minutes since a prisoner last ate. One who has never eaten is timed
-- from when this door first saw him.
local function unfedFor(prisoner, now, seen)
    local ate = tonumber(prisoner.LastAte)
    if ate ~= nil and ate > 0 then
        return now - ate
    end
    local id = prisoner.Id ~= nil and tonumber(prisoner.Id.i) or nil
    if id == nil then
        return 0
    end
    seen[id] = firstSeen[id] or now
    return now - seen[id]
end

-- The prisoners of this door's cell a bangup has kept from a meal, and
-- whether any of them is hungry enough to call a guard for. A prisoner who is
-- locked in is on a punishment and is the game's to feed, as is one the game
-- is already feeding.
local function bangedUp()
    local cell = this.CellId
    local cellId = cell ~= nil and tonumber(cell.i) or nil
    if cellId == nil or cellId < 0 then
        return nil, false
    end
    local now = tonumber(World.TimeIndex) or 0
    local list, hungry, seen = {}, false, {}
    for prisoner, _ in pairs(nearby("Prisoner", CELL_REACH)) do
        local home = prisoner.Cell
        if home ~= nil and tonumber(home.i) == cellId and prisoner.Locked ~= true
            and (tonumber(prisoner.Damage) or 0) < 1
            and (tonumber(prisoner.FeedJobId) or -1) < 0
            and unfedFor(prisoner, now, seen) >= UNFED_FOR then
            list[#list + 1] = prisoner
            local food = tonumber(Object.GetProperty(prisoner, "Needs.Food"))
            if food ~= nil then
                hungry = hungry or food >= FOOD_AT
            else
                hungry = hungry or clock - lastMeal >= MEAL_GAP
            end
        end
    end
    firstSeen = seen
    return list, hungry
end

local function watchMeals(timePassed)
    if mealOut then
        mealWait = mealWait + timePassed
        if mealWait >= MEAL_GIVE_UP then
            -- nobody came: withdraw it and ask afresh at the next look
            this.CancelJob(MEAL_JOB)
            mealOut = false
        end
        return
    end
    local list, hungry = bangedUp()
    if list ~= nil and hungry then
        this.CreateJob(MEAL_JOB)
        mealOut = true
        mealWait = 0
    end
end

-- The game calls this when a guard has finished the meal job at the door.
function JobComplete_LaserDoorMeal()
    mealOut = false
    lastMeal = clock
    local list = bangedUp()
    local now = tonumber(World.TimeIndex) or 0
    for _, prisoner in ipairs(list or {}) do
        Object.SetProperty(prisoner, "Needs.Food", 0)
        Object.SetProperty(prisoner, "LastAte", now)
    end
end

local function holdStill(timePassed)
    -- True once the engine has no slide left to apply to this door. Between
    -- rechecks the last answer stands.
    if held then
        holdTimer = holdTimer + timePassed
        if holdTimer < HOLD_RECHECK then
            return true
        end
        holdTimer = 0
    end
    held = false
    local dir = this.OpenDir
    if dir == nil then
        return false
    end
    local x, y = tonumber(dir.x), tonumber(dir.y)
    if x == nil or y == nil then
        return false
    end
    if x == 0 and y == 0 then
        held = true
        return true
    end
    if x ~= 0 then
        dir.x = 0
    end
    if y ~= 0 then
        dir.y = 0
    end
    held = tonumber(dir.x) == 0 and tonumber(dir.y) == 0
    return held
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

function Update(tick)
    stepTimer = stepTimer + tick
    if stepTimer < STEP then
        return
    end
    local timePassed = stepTimer
    stepTimer = 0

    local damage = shockAttackers(timePassed)

    local still = holdStill(timePassed)

    if damage >= BROKEN_AT then
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
    findTimer = findTimer + timePassed
    if findTimer >= findAfter then
        findTimer = 0
        lookAround()
    end
    staffTimer = staffTimer + timePassed
    if staffHold > 0 then
        staffHold = staffHold - timePassed
    end
    if staffTimer >= STAFF_EVERY then
        staffTimer = 0
        -- Those looks are most of what a door costs, and an unlocked door
        -- has no use for them.
        if (not controlled or lockout > 0) and staffAtDoor() then
            staffHold = STAFF_HOLD
            -- someone is here and the door is held: the next look can wait
            staffTimer = STAFF_EVERY - STAFF_RELOOK
        end
    end
    if scanTimer >= SCAN_INTERVAL then
        scanTimer = 0
        local open = staffHold > 0 or servoWantsOpen() or guardAtPanel()
        if open ~= remoteOpen then
            remoteOpen = open
            showTooltip()
        end
    end

    clock = clock + timePassed
    mealTimer = mealTimer + timePassed
    if mealTimer >= MEAL_CHECK_EVERY then
        local waited = mealTimer
        mealTimer = 0
        watchMeals(waited)
        -- The game hands a script every object a search finds as a global
        -- named for the object's type and id, and never takes one back, so a
        -- door would hold on to everyone it has ever seen. Clear them, and
        -- Lua's own collector frees what they held. Reading a property of an
        -- object goes through its global, so the servos and panels the door
        -- remembers between looks keep theirs.
        if _G ~= nil then
            for name, value in pairs(_G) do
                if type(value) == "table" and type(name) == "string" and name:find("i%-?%d+u%-?%d+$")
                    and not name:find("^Servo") and not name:find("^LaserDoorPanel") then
                    _G[name] = nil
                end
            end
        end
    end

    controlTimer = controlTimer + timePassed
    if controlTimer >= controlAfter then
        controlTimer = 0
        lookForController()
    end

    local raw = tonumber(this.Open) or 0
    if controlled and not remoteOpen and watchForTrouble(timePassed, raw) then
        raw = 0
        lastRaw = 0
    end
    local openness = raw
    if remoteOpen then
        openness = 1
        forced = true
        openFor = 0
    elseif forced then
        -- whatever held it open has gone, and the engine will not shut a
        -- door it did not open
        forced = false
        openness = 0
    elseif raw >= OPENED then
        openFor = openFor + timePassed
        if openFor >= STUCK_AFTER then
            openFor = 0
            openness = 0
        end
    elseif raw > SHUT and raw < OPENED then
        -- part-way: the engine is animating. Snap in the direction it is going.
        if raw >= lastRaw then
            openness = 1
        else
            openness = 0
        end
    end
    if raw < OPENED then
        openFor = 0
    end
    lastRaw = openness
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
