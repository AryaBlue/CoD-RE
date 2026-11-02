# T6 MP weapon spread, view kick and gun kick (t6mp.exe)

<!-- toc -->
## Contents

- [1. Where the fields live](#1-where-the-fields-live)
- [2. Dvars](#2-dvars)
- [3. Random numbers](#3-random-numbers)
- [4. Aim spread scale update (every pmove)](#4-aim-spread-scale-update-every-pmove)
- [5. Fire add (per shot)](#5-fire-add-per-shot)
- [6. Min/max spread for a weapon](#6-minmax-spread-for-a-weapon)
- [7. Spread used by a shot, and the shot direction](#7-spread-used-by-a-shot-and-the-shot-direction)
- [8. Crosshair](#8-crosshair)
- [9. View kick: per shot](#9-view-kick-per-shot)
- [10. View kick: decay and recentre](#10-view-kick-decay-and-recentre)
- [11. Gun (weapon-model) kick](#11-gun-weapon-model-kick)
- [12. Against the current Reforged code](#12-against-the-current-reforged-code)
- [Open](#open)
<!-- /toc -->

Static RE of the Steam `t6mp.exe` (x86, image base 0x400000). The exe is SteamStub 3.1 wrapped (`.text` AES-encrypted,
signature 0xC0DEC0DF, app 202990). It was decrypted into a scratch copy only; addresses below are VAs in that image and
are the same as the live game's. Nothing was run. Tags: **[V addr]** is read from code or data at that address,
**[I]** is inferred or a name guess.

Units used throughout: angles in **degrees**, `aimSpreadScale` is a **float 0..255** (ps+0x588), `frametime` is
**seconds** (pml+0x24), `msec` is integer ms (pml+0x28), view and gun kick velocities are **deg/s**.

## 1. Where the fields live

The weapon cspField table is at **0xF6E5A8** (1030 entries of `{const char* name; int offset; int type}`; type 8 =
float, 4 = int, 9 = msec) [V 0xF6E5A8]. Its offsets are into `WeaponFullDef`, which starts with `WeaponVariantDef`
(size 0x2CC) and then `WeaponDef` [V: OAT T6 layout matches, `AIOverlayDescription` → 0x2CC = `weapDef.szOverlayName`].
So **WeaponDef offset = table offset − 0x2CC**; offsets under 0x2CC are in the variant. Code gets them via
`BG_GetWeaponDef` **0x8E76E0** and `BG_GetWeaponVariantDef` **0x8E76C0** [V].

| field | table off | struct + off |
|---|---|---|
| hipSpreadStandMin / DuckedMin / ProneMin | 0x87C / 0x880 / 0x884 | WeaponDef +0x5B0 / 5B4 / 5B8 |
| hipSpreadMax / DuckedMax / ProneMax | 0x888 / 0x88C / 0x890 | +0x5BC / 5C0 / 5C4 |
| hipSpreadDecayRate | 0x894 | +0x5C8 |
| hipSpreadFireAdd / TurnAdd / MoveAdd | 0x898 / 0x89C / 0x8A0 | +0x5CC / 5D0 / 5D4 |
| hipSpreadDuckedDecay / ProneDecay | 0x8A4 / 0x8A8 | +0x5D8 / 5DC |
| hipReticleSidePos | 0x8AC | +0x5E0 |
| adsSpread | 0xAAC | +0x7E0 |
| adsGunKickReducedKickBullets (int) / Percent | 0xA5C / 0xA60 | +0x790 / 794 |
| adsGunKickPitchMin / Max, YawMin / Max | 0xA64..0xA70 | +0x798 / 79C / 7A0 / 7A4 |
| adsGunKickAccel / SpeedMax / SpeedDecay / StaticDecay | 0xA74..0xA80 | +0x7A8 / 7AC / 7B0 / 7B4 |
| adsViewKickPitchMin / Max | 0xA84 / 0xA88 | +0x7B8 / 7BC |
| adsViewKickMinMagnitude | 0xA8C | +0x7C0 |
| adsViewKickYawMin / Max | 0xA90 / 0xA94 | +0x7C4 / 7C8 |
| adsRecoilReductionRate / Limit / ReturnRate | 0xA98 / 0xA9C / 0xAA0 | +0x7CC / 7D0 / 7D4 |
| hipGunKickReducedKickBullets (int) / Percent | 0xAB0 / 0xAB4 | +0x7E4 / 7E8 |
| hipGunKickPitchMin / Max, YawMin / Max | 0xAB8..0xAC4 | +0x7EC / 7F0 / 7F4 / 7F8 |
| hipGunKickAccel / SpeedMax / SpeedDecay / StaticDecay | 0xAC8..0xAD4 | +0x7FC / 800 / 804 / 808 |
| hipViewKickPitchMin / Max | 0xAD8 / 0xADC | +0x80C / 810 |
| hipViewKickMinMagnitude | 0xAE0 | +0x814 |
| hipViewKickYawMin / Max | 0xAE4 / 0xAE8 | +0x818 / 81C |
| adsViewKickCenterDuckedScale / ProneScale | 0xAF4 / 0xAF8 | +0x828 / 82C |
| antiQuickScopeTime / Scale / SpreadMultiplier / SpreadMax | 0xAFC..0xB08 | +0x830 / 834 / 838 / 83C |
| **adsViewKickCenterSpeed** | 0x21C | **WeaponVariantDef +0x21C** |
| **hipViewKickCenterSpeed** | 0x220 | **WeaponVariantDef +0x220** |
| gunMaxPitch / gunMaxYaw | 0x8C8 / 0x8CC | WeaponDef +0x5FC / 600 |
| reticleSide / SideSize (int) / MinOfs (int) | 0x4E0 / 0x4E8 / 0x4EC | +0x214 / 21C / 220 |
| fireTime (msec) / fireDelay (msec) | 0x734 / 0x6FC | +0x468 / 430 |
| shotCount / minDamageRange | 0x69C / 0x6DC | +0x3D0 / 410 |
| weaponType / weaponClass / fireType | 0x2E8 / 0x2EC / 0x2FC | +0x1C / 20 / 30 |
| aimDownSight (bool) | 0x904 | +0x638 |

Attachment fields used here (WeaponAttachment, up to 3 per weapon via 0x8EB300) [V field table 0xC81384..]:
`hipSpreadMinScale` +0xA0, `hipSpreadMaxScale` +0xA4, `adsRecoilReductionRate` +0x54, `adsRecoilReductionLimit` +0x58,
`adsViewKickCenterSpeedScale` +0x5C, fire-time scale +0xBC [V 0x8EC740; name I].

playerState offsets (from the ps netfield tables at 0xC96xxx) [V]: `pm_type` 0x4, `velocity` 0x34/0x38,
`weaponRestrictKickTime` 0x6C, `speed` 0x94 (int), `groundEntityNum` 0xA4, `eFlags` 0xFC, `weapon` 0x1B8,
`weaponstate` 0x1D0 / `weaponstateLeft` 0x1D4, `fWeaponPosFrac` (ADS fraction) 0x1E0, `spreadOverride` 0x1E8,
`spreadOverrideState` 0x1EC, `viewHeightTarget` 0x204, `viewHeightCurrent` 0x208 (float), `chargeShotLevel` 0x4EC,
`quickScopeScale` 0x4F4, `quickScopeTimer` 0x4F8, `perks[0]` 0x548, **`aimSpreadScale` 0x588**.

## 2. Dvars

| dvar | default | used for | evidence |
|---|---|---|---|
| `bg_aimSpreadMoveSpeedThreshold` | 11 (min 0) | move add only above this horizontal speed | [V reg 0x8B8D44..0x8B8D77, ptr 0x314EA08] |
| `perk_weapSpreadMultiplier` | 0.65 (0..1) | perk scale on min/max | [V reg 0x8BECCB..0x8BECFE, ptr 0x3160F08] |
| `adsZeroSpread` | 1 | zero `aimSpreadScale` when fully ADS | [V reg 0x8BB7C0, ptr 0x3150C4C] |
| `bg_aqs` | 1 | anti-quick-scope spread add | [V reg 0x8BB770, ptr 0x314E948] |
| `player_standingViewHeight` | 60 (int) | stance lerp top | [V reg ~0x8B9C48, ptr 0x3150B24] |
| `player_disableWeaponsOnVehicle` | 1 | vehicle-velocity move add is skipped while this is 1 | [V reg 0x8B9C6D, ptr 0x314E9A8] |
| `bulletrange` | 8192 | bullet trace length (non-spread classes) | [V reg 0x6E88D4..0x6E8907, ptr 0x282D7B8] |
| `tu12_zm_stack_fire_fix` | 0 | stacked-fire exponent source | [V ptr 0x314EA64] |
| `cg_crosshairAlpha` / `cg_crosshairAlphaMin` | ? / 0.5 | crosshair fade | [V reg 0x4D2B31..0x4D2B9C; Alpha default I, probably 1] |

No other dvar scales spread or kick in these paths. `bg_viewKickScale` (ptr 0x3150BDC) is the **damage** kick
(0x4E8AB0), not weapon recoil [V].

## 3. Random numbers

`BG_random` **0x8C3B20**: `seed = seed*0x343FD + 0x269EC3; return (seed >> 17) * (1/32768)` → [0,1), 15-bit [V].
`BG_srand`-style scramble **0x8C3AB0**: `c = seed & 0xFF; seed ^= (c<<8) ^ (c<<16) ^ (c<<24)` [V].
**0x8C55B0** steps the LCG four times and discards [V].

## 4. Aim spread scale update (every pmove)

`PM_UpdateAimSpread`-like **0x8E0080**, called near the top of PmoveSingle [V call 0x8C8B74], before weapon logic.

```
wd = weapDef(ps->weapon)
decay = wd.hipSpreadDecayRate                       ; per second, fraction of full scale
sub   = 1.0 ; ratio = 1.0                           ; NB decay == 0 => sub = 1.0 => scale -= 255 (snaps to 0)
if decay != 0:
    ratio = (spreadOverride - StandMin) / (Max - StandMin)
    if groundEntityNum == 1023 && pm_type != 1:     ; in the air [I: pm_type 1 meaning]
        decay *= 0.5
    elif eFlags & 0x8:                               ; prone
        decay *= ProneDecay;  ratio = (spreadOverride - ProneMin)/(ProneMax - ProneMin)
    elif eFlags & 0x4:                               ; crouched
        decay *= DuckedDecay; ratio = (spreadOverride - DuckedMin)/(DuckedMax - DuckedMin)
    if spreadOverrideState == 1:
        sub = frametime * decay / ratio
    else:
        sub = frametime * decay
        if adsFrac == 1.0 && (!bg_aqs || quickScopeTimer == 0):
            if adsZeroSpread: aimSpreadScale = 0
            ; no add at full ADS, just decay
        else:
            add = AntiQuickScopeAdd()                ; 0x8DBFB0, 0 for most weapons
            if TurnAdd != 0:
                for axis in pitch, yaw:
                    d = AngleNormalize180(SHORT2ANGLE(cmd.angles[i]) - SHORT2ANGLE(oldcmd.angles[i]))
                    add += |d| * 0.01 * TurnAdd / frametime          ; TurnAdd per 100 deg/s
            if MoveAdd != 0:
                if cmd.forwardmove || cmd.rightmove:                   ; pm+0x28/+0x29 [I names]
                    v = |ps.velocity.xy|
                    if v > bg_aimSpreadMoveSpeedThreshold:
                        add += v * MoveAdd / ps.speed                    ; ps.speed = g_speed int (0x94)
                ; + an extra term from a linked vehicle's velocity, only if player_disableWeaponsOnVehicle == 0
            if in the air: add += 2.56                                  ; 1.28 + 1.28 [V 0xBD73A0]
            add *= frametime
            if add > 0:
                aimSpreadScale += add * 255                             ; and NO decay this frame
                goto clamp
aimSpreadScale -= sub * 255
clamp:
if spreadOverrideState == 1 && aimSpreadScale*ratio < 255:
    spreadOverrideState = 0; aimSpreadScale *= ratio
aimSpreadScale = clamp(aimSpreadScale, 0, 255)
```

All [V 0x8E0080–0x8E05A4] except the bracketed names. Points that matter for matching:
- Decay is **skipped entirely in any frame that adds** (moving above 11 u/s with MoveAdd > 0, turning, airborne, AQS).
  Firing does not stop decay: the fire add is applied separately (section 5).
- Stance picks decay by **eFlags** bits (prone 0x8, crouch 0x4), but the min/max in section 6 use the view height.
- Stance decay factors **multiply** DecayRate; airborne halves it.
- MoveAdd is "per second at full run speed": at v = g_speed it adds `MoveAdd*255` per second.
- Constants: 0.00549316 = 360/65536 [V 0xB2875C], 1/360 [V 0xC73650], 0.01 [V 0xC73410], 255 [V 0xC733A0].

Anti-quick-scope add **0x8DBFB0** [V]: returns 0 unless `bg_aqs` and `quickScopeScale > 1` and
`aimSpreadScale <= antiQuickScopeSpreadMax` and `quickScopeTimer == int(antiQuickScopeTime*1000)`; then returns
`(quickScopeScale - 1) * antiQuickScopeSpreadMultiplier`. How quickScopeScale/Timer are driven is not traced [I].

## 5. Fire add (per shot)

**0x8DC710**, called from the fire path 0x8E1B80 at [V 0x8E1F36] once per shot, right after the fire event:

```
if adsFrac != 1.0: aimSpreadScale = min(aimSpreadScale + hipSpreadFireAdd*255, 255)
```
[V 0x8DC710]. At full ADS the shot adds nothing (and `adsZeroSpread` zeroes it next frame anyway).

## 6. Min/max spread for a weapon

`BG_GetSpreadForWeapon(ps, weapon, &min, &max)` **0x8E41A0** [V]:

```
if spreadOverrideState == 2: min = max = spreadOverride
else:
    vh = ps.viewHeightCurrent                       ; float, continuous during stance changes
    if vh <= 40:
        f = (vh - 11) / 29                          ; 0.0344828 [V 0xBD7410]
        min = ProneMin + (DuckedMin - ProneMin) * f;  max = ProneMax + (DuckedMax - ProneMax) * f
    else:
        f = (vh - 40) / (player_standingViewHeight - 40)
        min = DuckedMin + (StandMin - DuckedMin) * f; max = DuckedMax + (Max - DuckedMax) * f
if fireType == 6 (stacked) && clipSize > 1:          ; zombies weapons, [I] 0x8E5E50 = clip size
    k = stackFireAccuracyDecay ^ (clipSize - 1)      ; or ^(ps+0x560 - 1) with tu12_zm_stack_fire_fix
    min *= k; max *= k
if spreadOverrideState == 1: max = spreadOverride
min *= prod(att.hipSpreadMinScale); max *= prod(att.hipSpreadMaxScale)       ; 0x8ED330
if sessionModeBit(4):                                ; 0x6BF700(4) [I which mode]
    if hasPerk(7) && adsFrac < 1: min,max *= perk_weapSpreadMultiplier
else:
    if hasPerk(3): min,max *= perk_weapSpreadMultiplier   ; perk 3 [I] = specialty_bulletaccuracy (Steady Aim)
```

So stance is **not** a three-way switch: the pair is lerped by the live view height (11 prone, 40 crouch, 60 stand),
so spread slides during stance transitions. No clamp on f [V].

## 7. Spread used by a shot, and the shot direction

The shot uses the **pre-pmove** scale: the server copies `client->currentAimSpreadScale = ps.aimSpreadScale / 255`
at [V 0x5DC1F3] inside ClientThink before its pmove call ([I] 0x8C9490 at 0x5DCE3C is Pmove), and the client copies
`cg+0x80B5C = predictedPlayerState.aimSpreadScale` at the top of CG_PredictPlayerState [V 0x4ECDBA]. So a shot does
not see its own frame's FireAdd/decay.

Server `FireWeapon` **0x66E590** (client mirror inside **0x535F80**, same formula [V 0x536140]):
```
s = currentAimSpreadScale                            ; 0..1
GetSpreadForWeapon(ps, weapon, &min, &max)
if adsFrac == 1.0: spread = adsSpread + (max - adsSpread) * s     ; exact == 1.0 [V ucomiss 0x66E66E]
else:              spread = min + (max - min) * s
```
There is **no ADS-fraction lerp**: until the ADS fraction is exactly 1 the shot uses full hip spread; at 1 it is
`adsSpread` lerped towards hip max by the scale (which `adsZeroSpread` keeps at 0) [V 0x66E66E–0x66E6AB].

`Bullet_Fire` **0x5D0C20** (weaponType 0 = bullet) [V]:
```
if weaponClass in (3, 13):  shots = shotCount; range = minDamageRange * attachRangeScale(0x8ED030)   ; [I class names: spread]
else:                       shots = 1;         range = bulletrange (8192)
seed = gameTime-ish arg; scramble(seed)              ; 0x8C3AB0 [I that the arg is the shot's game time]
aim = tan(spread * pi/180) * range                   ; 0xA2435A = tan
per shot:
    theta = BG_random(seed) * 360                    ; degrees
    skip4(seed)                                      ; 0x8C55B0
    r     = BG_random(seed)                          ; uniform 0..1, NOT sqrt
    end   = start + fwd*range + right*(cos(theta)*r*aim) + up*(sin(theta)*r*aim)
    dir   = normalise(end - start)
```
Distribution: a disc of radius tan(spread) at unit distance with **radius uniform** (centre-weighted, density ∝ 1/r),
angle drawn first. [I] which of wp[3..5]/wp[6..8] is right vs up (irrelevant, theta is uniform).

## 8. Crosshair

`CG_DrawCrosshair`-like **0x4B5EA0**, size from **0x4B5D70** [V]:
```
GetSpreadForWeapon(ps, weapon, &min, &max)
deg  = (min + (max - min) * predictedPs.aimSpreadScale/255) * k        ; k = caller's scale arg [I]
ofs  = tan(deg * pi/180) * 240 / cg.refdef.tanHalfFovY                  ; cg+0x4D8B4 [I name], 240 = half of 480
ofs  = max(ofs, reticleMinOfs)
side = reticleSideSize * k;  per-axis pos = ofs - side * hipReticleSidePos
alpha = cg_crosshairAlpha * fadeIn * (1 - aimSpreadScale/255), floored at cg_crosshairAlphaMin    ; 0x4B5E40
```
It uses the **current** predicted scale (cg+0x48630), not the pre-pmove copy, and ignores adsSpread. Four side pieces
at 0/90/180/270 degrees, half-size layout when an unnamed bool dvar (ptr 0x34C7494) is set.

## 9. View kick: per shot

`BG_WeaponFireRecoil(ps, vGunSpeed, kickAVel, &lastRecoilTime, accumulate, &recoilAmount, &seed)` **0x8E3A00** [V].
Called by CG_FireWeapon [V 0x53A069] for the local first-person player (`accumulate = cg+0x695EC > 0`, a
continuous-fire shot counter [I]) and server-side on fire events [V 0x5D17E3].

```
ads  = (adsFrac == 1.0)                              ; exact, for view kick and ReducedKickPercent
red  = 1.0
if ps.weaponRestrictKickTime > 0:
    red = (ads ? adsGunKickReducedKickPercent : hipGunKickReducedKickPercent) * 0.01
if ads:
    pMin,pMax,yMin,yMax,minMag = adsViewKick...
    (rate, limit) = adsRecoilReduction with attachment overrides         ; 0x8ECD00
    if rate > 0:
        amt = accumulate ? recoilAmount + rate
                         : max(recoilAmount - (now - lastRecoilTime)*0.001*adsRecoilReturnRate, 0)
        amt = clamp(amt, 0, limit)
        pMin,pMax,yMin,yMax *= (1 - amt)
    pitch = lerp(pMin, pMax, rand());  yaw = lerp(yMin, yMax, rand())
    m = (1 - rate) * minMag                          ; min magnitude also scaled by (1 - rate)
else (hip, single weapon):
    pitch = lerp(hipVKPitchMin, Max, rand());  yaw = lerp(hipVKYawMin, Max, rand())
    m = hipViewKickMinMagnitude
if |(pitch, yaw)| < m: scale (pitch, yaw) up to length m             ; [V 0x8E3F2D]
lastRecoilTime = now; recoilAmount = amt
kickAVel[0] = -|pitch| * red                          ; always up; weaponType 4 with kickAVel[0]==0 gets -0.001
kickAVel[1] =  yaw * red
kickAVel[2] =  yaw * red * -0.5                       ; roll
```
- kickAVel is **assigned**, not added; the previous shot's remaining velocity is overwritten [V tail of 0x8E3A00].
- Hip/ADS is **binary** on adsFrac == 1.0, no lerp.
- Dual wield (0x8EB9C0 true): hip values are the sum of both guns' ranges for whichever hands are firing
  (weaponstate 6 or 0x28), and no min magnitude is applied [V].
- fireType 8 (charge shot) with chargeShotLevel > 1: pitch = `pitch + pitch*chargeShotLevel*
  bg_chargeShotViewKickIncreasePerBullet`, capped at `bg_chargeShotMaxViewKick` [V dvars 0x3150C6C / 0x3150B70].
- Random source: a persistent module LCG state (`&holdrand`, 0x74B4E0 returns 0xCA3568 on the client, 0x64A970 returns
  0xC90A40 on the server, both initialised to 0x89ABCDEF) [V]. Draw order: pitch, yaw, then gun pitch, gun yaw.
- In the shipped MP weapon files only `hamr_mp` / `dualoptic_hamr_mp` have adsRecoilReductionRate > 0 (0.03, limit
  0.15, return 1) [V weapon files].

Reduced kick timer [V 0x8DC3D1, 0x8E0825]: when a trigger pull starts (weaponstate not 6/0x28),
`weaponRestrictKickTime = fireTime*(adsFrac < 1 ? hipReducedKickBullets : adsReducedKickBullets) + fireDelay`
(fireTime includes attachment scales, 0x8EC740). Each pmove subtracts `msec`, floored at 0. So the first N shots of a
burst get `ReducedKickPercent`% of the view and gun kick.

## 10. View kick: decay and recentre

Client **0x51F150** (server mirror 0x5D6D50 reads the same fields [V 0x5D6E40..0x5D6F0D]; details assumed equal [I]).
State: `kickAVel` cg+0x697BC, `kickAngles` cg+0x697C8 [V].

```
for t = cg.frametime msec; t > 0; t -= 5:
    dt = min(t, 5) * 0.001
    for axis in 0..2:
        if kickAngles == 0 && kickAVel == 0: continue
        if kickAngles != 0:
            sgn = kickAngles > 0 ? -1 : +1
            if no weapon:            c = 2400
            elif adsFrac > 0.5:      c = variant.adsViewKickCenterSpeed * prod(att.adsViewKickCenterSpeedScale)
                                     c *= stance==prone ? adsViewKickCenterProneScale
                                        : stance==crouch ? adsViewKickCenterDuckedScale : 1
            elif dual wield:         c = sum of variant.hipViewKickCenterSpeed of the firing hand(s)
            else:                    c = variant.adsViewKickCenterSpeed      ; sic, see note
            kickAVel += sgn * c * dt                          ; c is an angular acceleration, deg/s^2
        d = kickAVel * dt
        if kickAngles * d < 0: d *= 0.06                      ; moving back to centre is 16x slower
        if (kickAngles + d) * kickAngles < 0: kickAngles = 0; kickAVel = 0     ; crossed centre
        else:
            kickAngles += d
            if kickAngles == 0 || |kickAngles| > 10: kickAngles = clamp(+-10); kickAVel = 0
```
[V 0x51F150–0x51F43C]. Stance here is from `viewHeightTarget` via **0x8BFA60**: 11 → prone, 40 → crouch, else stand
(22 is a special case on ps+0x5B8) [V].

**Note (quirk, [V])**: for a single (non-dual-wield) weapon both the hip branch (adsFrac ≤ 0.5) [V 0x51F3E5] and the
ADS branch [V 0x8ECFB5] read variant **+0x21C**, which the field table names `adsViewKickCenterSpeed`;
`hipViewKickCenterSpeed` (+0x220) is only read for dual wield. The weapon files agree with this: every `_dw`/`_lh`
file has ads 0 / hip 1100, and e.g. `dsr50_mp` has ads 750 / hip 500 (the 500 is never used).

The ducked/prone centre scales apply only above 0.5 ADS. The kick angles are added to the view angles by code not
traced here [I].

## 11. Gun (weapon-model) kick

Per shot (inside 0x8E3A00) [V]: if `adsFrac > 0` (note: **> 0**, not == 1) use the ADS gun ranges, else hip
(dual wield sums like the view kick):
```
vGunSpeed[0] += lerp(GunKickPitchMin, Max, rand()) * red
vGunSpeed[1] += lerp(GunKickYawMin,   Max, rand()) * red      ; added, not assigned
```
Integration **0x8F0700** (called from CG 0x5375C9 and server 0x5DCCBF), only when `aimDownSight` is set [V 0x8DA830]:
```
f = adsFrac
accel  = lerp(hipGunKickAccel,      adsGunKickAccel,      f)
vmax   = lerp(hipGunKickSpeedMax,   adsGunKickSpeedMax,   f)
sdecay = lerp(hipGunKickSpeedDecay, adsGunKickSpeedDecay, f)
static = lerp(hipGunKickStaticDecay,adsGunKickStaticDecay,f)
for remaining = frametime (s); remaining > 0; in 0.005 s slices, stop early once both axes are at rest:
    for axis (pitch: limit gunMaxPitch, yaw: limit gunMaxYaw):
        if |ofs| < 0.25 && |spd| < 1: ofs = spd = 0; continue          ; at rest
        ofs += dt * spd
        if ofs >  limit: ofs =  limit; if spd > 0: spd = 0
        if ofs < -limit: ofs = -limit; if spd < 0: spd = 0
        if ofs > 0: spd -= dt*accel  elif ofs < 0: spd += dt*accel     ; spring to centre
        spd -= spd * sdecay * dt                                       ; proportional damping
        spd  = spd > 0 ? max(spd - dt*static, 0) : min(spd + dt*static, 0)   ; constant friction
        spd  = clamp(spd, -vmax, vmax)
```
[V 0x8F0700–0x8F0990]. Gun kick, unlike view kick, **lerps** hip→ADS by the ADS fraction. `vGunOffset` (degrees) is
then fed into the view-model angle build (0x8F0160/0x8F0340) [I exact use].

## 12. Against the current Reforged code

- `AimSpread` keeps the scale 0..1; T6 is 0..255 but every add/decay is `x*255`, so 0..1 with the same per-second
  rates is equivalent. What differs: decay is skipped in frames that add; move add is `speed/g_speed * MoveAdd` above
  11 u/s (not a clamped fraction); turn add is `|Δdeg|/s * 0.01`; airborne adds 2.56/s and halves decay; FireAdd is
  skipped at full ADS; DecayRate 0 snaps the scale to 0.
- `degrees()`: the stance pair should lerp by view height, and ADS is not a lerp: `adsFrac == 1 ? adsSpread +
  (max - adsSpread)*s : min + (max - min)*s`; the perk multiplier (0.65) and attachment scales go on min/max.
- `spreadDirection()`: already radius-uniform; T6 draws theta first, skips 4 LCG steps, then r.
- `ViewKick`: kick is an angular velocity set per shot (abs pitch up, roll = -0.5*yaw), min magnitude, then a
  constant-acceleration spring at CenterSpeed with 0.06x return speed and a ±10° clamp, in 5 ms steps; not
  exponential. Use the ADS centre speed for single-weapon hip too.

## Open

- [I] Exact meaning of `pm_type != 1` in the airborne test, the session-mode bit tested by 0x6BF700(4) and which
  perks indices 3 and 7 are.
- [I] Shot seed source (the `param_5` passed into Bullet_Fire is assumed to be the shot's game time) and the CG
  bullet-endpos mirror for prediction (not decompiled).
- [I] Server kick-centre 0x5D6D50 assumed identical to the client one.
- [I] How quickScopeScale/quickScopeTimer evolve (anti-quick-scope, snipers only).
- [I] How kickAngles and vGunOffset are applied to the view and view model.
- Nothing here was checked in game.
