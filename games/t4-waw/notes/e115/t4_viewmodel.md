# T4 viewmodel placement

Where WaW draws the first-person gun and arms, and why Reforged's colt sits too far back.

Tags:
- **[V]**: zone data (the inflated `common.ff` / Nacht zone), a raw weapon file, or `t4sp.exe` VA.
- **[M]**: measured in game. None yet.
- **[I]**: inferred.

## Update: the hip offset is frame 0 of the ADS anim

After the rest-pose fix in the decoder the colt still sat on the eye. **The missing offset is `tag_torso`, and only the
ADS anims drive it.**

- **What they drive** [V]: `viewmodel_colt45_ads_up`, `_ads_down` and `viewmodel_kar98_ads_down` each drive **one bone,
  `tag_torso`** (trans + quat). The idle, fire and ads_fire anims never touch it.
- **The frames line up** [V]:
  - `ads_up` frame 0 = `ads_down` last frame = the **hip** pose.
  - `ads_up` last frame = `ads_down` frame 0 = the **ADS** pose.
- **`tag_torso` local, in CoD axes (fwd, left, up)** [V, decoded]:

  | anim | hip | ADS | hip quat |
  |---|---|---|---|
  | colt45 | **(11.42, −4.16, −2.44)** | (7.91, 0.24, 0.41) | ≈ identity |
  | kar98 | **(2.59, −2.83, −3.46)** | (3.54, −0.32, −0.19) | ≈ identity |

  So the colt hip is 4.16 right and 2.44 down, and the kar98 is 2.83 right and 3.46 down. [M] Low-right in Reforged
  (lead, 2026-10-27), matching WaW.
  - Axis gotcha: in the export glb, the node rests and these single-bone `tag_torso` tracks are raw CoD axes. The
    72-bone idle/fire channels in the same file come out in the decoder's (x, z, −y) frame. Don't apply one convention
    to the whole file.

  - colt `ads_up`: 10 frames at 24 fps.
  - colt `ads_down`: 12 frames at 24 fps.
  - kar98 `ads_down`: 16 frames at 30 fps.
- **So the hip colt grip sits at about (13.2, −4.4, −4.5) and the muzzle at about (18.7, −4.3, −3.4)** relative to the
  eye (`tag_torso` + `tag_weapon` (1.81, −0.22, −2.07) + `tag_flash` (5.43, 0.09, 1.16)).
  - That's about 19° right and 19° below the view axis, with the hand in view.
- **ADS sanity check** [V numbers, M by lead]: the ADS colt `tag_weapon` lands at (9.72, 0.02, −1.66), and the muzzle
  about 0.5 below the eye on the centre line. That's where the front sight should be.
- **How the engine uses them** [I: standard CoD behaviour, the T4 blend code wasn't read]:
  - The ADS anim is always applied, at **time = weapon position fraction** (0 at the hip, 1 at full ADS).
  - It plays up or down depending on the direction.
  - Bones blend per bone: `tag_torso` comes only from the ADS anim; everything else comes from idle, fire and so on.
  - There's no position offset in code. This matches the "no ADS position fields" finding in §1.

**For Reforged:** for a viewmodel, always sample the weapon's `adsUpAnim` at t = adsFrac × length, or `adsDownAnim` at
(1 − adsFrac) × length when going down. Write its `tag_torso` into the pose over the idle/fire pose. At the hip this is
frame 0 of `ads_up`.

## Short answer (before the rest-pose fix)

**The colt's anim data is genuine. The misplacement comes from the rest pose the decoder gives `tag_torso`.**

- **The rig.** `viewmodel_hands_no_model` (the weapons' `handModel`) has 70 bones and one root, **`tag_view`** [V].
  - Its **local bone translations are all zero.** The 69 × 12-byte trans block is all zero bytes.
  - Only the rotations are set: shoulders and elbows have local quats; `tag_torso`, `tag_weapon`, `tag_ads`,
    `tag_cambone` and `tag_camera` are identity.
- **The decoder's rest pose.** `e115_zonedump --xanim` takes its rest pose from the bind matrices (`baseMat`). It warns
  "model locals disagree with baseMat on 66 (worst 16.596 units)".
  - So `tag_torso` gets a rest of **(−4.63, 0, −1.38)** and `tag_weapon` (15.16, 0, −6.75) [V, from the exported glb].
  - The baseMat values are the skinning bind. **They aren't the pose the engine animates from** [I: strong; CoD's
    DObj uses the model's local quats/trans for any bone the anim doesn't drive].
- **Neither anim drives `tag_view` or `tag_torso`** [V: no channels in the export]. So in game `tag_torso` sits
  exactly on `tag_view`, while Reforged moves it 4.63 back and 1.38 down.
- **`tag_weapon` is driven by the anim** (relative to `tag_torso`), and `j_gun` of the gun model attaches there:

  | anim, frame 0 | `tag_weapon` (fwd, left, up) | `j_shoulder_ri` | in game: grip / muzzle ahead of the eye | in Reforged's export |
  |---|---|---|---|---|
  | `viewmodel_colt45_idle` | (1.81, −0.22, −2.08) | (−19.97, 0.72, 0.48) | **1.8 / 7.2** | **−2.8**: behind the eye, off-screen |
  | `viewmodel_kar98_idle` | (7.89, 0.34, −1.65) | (−4.93, −0.73, −0.07) | 7.9 / 35.7 | 3.3: still visible, so it "looks right" |

  The muzzle is `tag_weapon` + `tag_flash`. `tag_flash` is 5.43 forward of `j_gun` on the colt and 27.85 on the kar98
  [V].
- **The 15-unit colt/kar difference is real.** The pistol anims hold the right shoulder about 15 units further back,
  with the arm extended. **The bug is the shared 4.63 back / 1.38 down.** The colt simply can't absorb it, because its
  grip is only 1.8 in front of the eye.
- **Fix:** for viewmodel rigs, use the model's local translation (zero here) for bones the anim doesn't drive, not
  `baseMat`. Keep `baseMat` for the inverse bind only.

## 1. View origin → viewmodel origin [V] (`t4sp` `0x469b50`, the view-weapon add)

1. **Hand position.** `0x466ee0` starts the hand at zero offset. It adds:
   - bob/sway, a sine term scaled by 1.6 and −2 (`0x466f15-0x467083`)
   - the movement/stance offset from `0x465ff0`, stored at client `+0xad020`

   Then `0x465a30` and `0x465ce0` run first [I: angles and sway].
2. **Add `cg_gun_x/y/z` along the view axes.** The axes are `0x352b6a8..6c8` (forward, right, up):
   origin += f × `cg_gun_x` + r × `cg_gun_y` + u × `cg_gun_z` (`0x469c16-0x469ce2`).
   - **All three default to 0** (registered at `0x65fc4f-0x65fce9`).
3. **`0x4672f0`** adds the weapon's own position offsets (below). The angles go to an axis (`0x5e25d0`), and
   `0x4697a0` adds the viewmodel to the scene with **its model origin at that point**.
   - `tag_view` is never looked up by name. The exe has no `tag_view` or `tag_torso` string [V], so there's no tag-based
     correction.

**Movement and stance offsets.** These are small, lerped, and in inches.
- **Dvars:** `cg_gun_move_f/r/u`, `cg_gun_ofs_f/r/u` ("weapon offset when prone/ducked") and `cg_gun_rot_p/y/r` all
  default to 0. They're read in `0x466150-0x4663ab`.
- **Weapon fields** [V raw files]:

  | field | colt | kar98k | thompson |
  |---|---|---|---|
  | `standMoveF/R/U` | 0 / 2.5 / −2.5 | 0 / 0 / −2 | 0 / 0 / −2.5 |
  | `duckedOfsF/R/U` | −0.8 / 1.2 / −1 | −0.2 / 0.5 / −0.2 | −1 / 0.3 / 0 |
  | `proneOfsF/R/U` | 1.2 / 3 / 0 | 0 / 1.6 / 1 | −1.5 / 2 / 0.5 |
  | `sprintOfsF/R/U` | 3 / −4 / −5 | 5 / −12 / −12 | −1.5 / −5 / 0.5 |
  | `posMoveRate` / `posRotRate` | 10 / 10 | 6 / 7.5 | (file) |

  - [I] `standMove*` applies with movement speed (`standMoveMinSpeed` 0).
  - [I] The ducked/prone/sprint offsets blend in at `posMoveRate`.
  - **None of these is anywhere near 15 units.**

**ADS:**
- There are no ADS position fields. ADS placement comes from the **`adsUpAnim` / `adsDownAnim`** viewmodel anims
  (`viewmodel_colt45_ads_up/_down`, `viewmodel_kar98_ADS_up`) [V field list].
- The hands rig carries `tag_ads` (identity, on `tag_view`).
- [I] The ADS anims are blended by the weapon position fraction over `adsTransInTime`/`OutTime` (colt 0.245/0.25,
  kar98k 0.2/0.4).

## 2. What the anim is relative to [V]

- **Root:** `tag_view` is bone 0 and the only root. The viewmodel's model origin is `tag_view`.
- **Chain:** `tag_torso` and `tag_cambone` are children of `tag_view`. `tag_weapon` and the shoulders are children of
  `tag_torso` (from the hands model's parent list).
- **No driven root:** the colt45 and kar98 idle/fire/pullout anims have no `tag_view` track and no `tag_torso` track,
  so both stay at the model local (identity).
- **So frame 0 is applied relative to the model origin = `tag_view` = the hand origin from §1**, with `tag_torso`
  coincident.
- **No root motion:** viewmodel anims carry no delta part.

## 3. Projection [V]

- **No separate gun fov.** There's no `cg_gun_fov`, `cg_fovViewmodel` or similar string in `t4sp.exe`. The viewmodel
  uses the scene fov:
  - `cg_fov` default 65 (1-160)
  - × `cg_fovScale`
  - lerped to the weapon's `adsZoomFov` when ADS (colt 60, kar98k 40, thompson 55)

  [I: the same frustum as the world.]
- **Its own near plane:**
  - The world's near plane is `r_znear` = **4** (0.001-10000).
  - The view weapon is drawn in the depth-hack pass with **`r_znear_depthhack` = 0.1** (0.001-16) (`0x707ece-0x707f34`).
  - **The colt grip at 1.8 needs that.** With a near plane of 4 it would clip. [I] The depth hack also keeps the gun
    from poking into walls.
- **Viewmodel depth of field:** `r_dof_viewModelStart`/`End` (defaults not read).

## For Reforged [I]

1. **Rest pose:** bones the anim doesn't drive use the model's local trans/quats, not `baseMat`.
2. **Placement:** viewmodel origin = camera + view-axis × (`cg_gun_x/y/z` = 0), plus the small stance/move offsets and
   bob.
3. **Near plane:** draw the viewmodel with the scene fov but a 0.1 near plane, in its own depth range.

**To prove it:** after fix 1, the colt grip should sit 1.8 forward and 2.1 down of the camera, with the muzzle at
about 7.2.

## Open

- [I] The exact blend of the stance/sprint offsets (`0x466150-0x4663ab`) and the bob terms.
- [I] Confirming in `XAnimCalc` that undriven bones take the model locals. It matches CoD behaviour, but that function
  wasn't read.
- [M] A side-by-side screenshot against the real game.
