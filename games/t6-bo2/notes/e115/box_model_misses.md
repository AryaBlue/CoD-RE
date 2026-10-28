# Box models left out of conversion (L10)

Why the mystery box teddy, the Ray Gun Mark II world model and Der Riese's `zombie_bowie_flourish` don't convert on some
maps, with a fix for each. Researched 2026-10-27 from the `convert_misses.txt` files, OAT zone listings and zonedump runs.

## Conventions

- **Tags:**
  - **[V]** read in data, or reproduced with zonedump.
  - **[I]** inferred.
- **Sources:**
  - OAT `Unlinker --list` of the zones;
  - the decompiled T6 box scripts;
  - zonedump run with the same arguments as the convert job.

## Summary

| map | job | cause | fix |
|---|---|---|---|
| Nacht | box model `zombie_teddybear` | Nacht has no teddy, and the model isn't in its zone | don't plan the teddy when the map's rule is `None` |
| Mob of the Dead | box model `zombie_teddybear` | prison's box joker is a lock, not a teddy; no teddy in the zone | plan the map's joker model |
| Buried, Origins | box model `t6_wpn_zmb_raygun2_world` | the map zone has only a reference; the real asset is in `patch_zm.ff` | load `patch_zm.ff` for t6 zombies box models |
| Der Riese | weapon `zombie_bowie_flourish` | its gun model is rigid (no bones), and the attach path required a skin | zonedump: a rigid part on a tag gets a joint of its own (tree) |

## Nacht: no teddy [V]

- `nazi_zombie_prototype.ff` has no `zombie_teddybear` xmodel. The listing has no teddy asset at all.
- Nacht's script has no teddy and no box move ([nacht_weapons_economy.md](../../../t4-waw/notes/e115/nacht_weapons_economy.md)). GameProfile already says so: `TeddyRule::None`.
- **The bug:** `Convert.cpp` (box models, ~line 420) inserts `zombie_teddybear` whenever the pool has a model, whatever the rule.
- **Fix:** add the teddy only when `bm->teddy != TeddyRule::None`. Nothing is lost, since Nacht never shows one.

## Mob of the Dead: the joker is a lock [V]

- `_zm_magicbox_prison.gsc` sets `level.chest_joker_model = "p6_anim_zm_al_magic_box_lock_red"` and puts that model on the box in place of the teddy.
- `zm_prison.ff` holds `p6_anim_zm_al_magic_box_lock` and `p6_anim_zm_al_magic_box_lock_red`, and **no `zombie_teddybear`**.
- **Origins:** `_zm_magicbox_tomb.gsc` sets the joker back to `zombie_teddybear`, which is in `zm_tomb.ff`.
- **Every other t6 map:** the default comes from `_zm_magicbox.gsc` (`zombie_teddybear`). Transit, Die Rise, Nuketown and Buried all have it in their zones.
- **Fix:**
  - give `BoxMap` a joker model (default `zombie_teddybear`; zm_prison `p6_anim_zm_al_magic_box_lock_red`);
  - have Convert plan that name;
  - `zm::MysteryBox::kTeddy` should read it from the map rather than a constant.
  - The prison box's own lock behaviour (Brutus) is a separate mechanic, already listed as later.

## Buried and Origins: Ray Gun Mark II lives in patch_zm [V]

- In `zm_buried.ff` and `zm_tomb.ff` the four `t6_wpn_zmb_raygun2_*` xmodels are **references** (OAT lists them as `,t6_wpn_zmb_raygun2_world`). zonedump skips references.
- The defined assets are in **`patch_zm.ff`** (all four: view, world, upg_view, upg_world).
- **Reproduced:**
  - `e115_zonedump zm_tomb.ff --game … --xmodel t6_wpn_zmb_raygun2_world` → "xmodel t6_wpn_zmb_raygun2_world isn't defined in the loaded zones";
  - the same with `--load patch_zm.ff` → exported (4 surfaces, 3812 tris, 7 textures).
- **Cause:** `GameProfile::weaponDependencyZones` returns nothing for t6 zombies, so the box-model jobs load no shared zone.
- **Fix:**
  - an optional t6 zombies load of `patch_zm.ff`, at least for the box-model jobs;
  - the named-xmodel path already lets the main zone win over `--load` zones, so the map's own models are unaffected.
  - Adding it to the `--weapons` job too would also pick up patch_zm's weapon defs [I: check that the gun list doesn't change before doing that].
- Nuketown, Transit and Die Rise don't hit this: their box pool doesn't include the Mark II, or their zone defines it [I: no misses there].

## Der Riese: the bowie flourish [V]

- **The weapon:** `zombie_bowie_flourish` (factory weapons.json) is an `item` with:
  - gunModel `viewmodel_knife_bowie`;
  - raise `viewmodel_zombie_bowie`;
  - idle/lower `viewmodel_zombie_perksacola_*`.
- **The job:** the convert plans `--xanim … "viewmodel_usa_marine_arms,viewmodel_knife_bowie@tag_weapon"`, and zonedump stopped with **"xmodel viewmodel_knife_bowie has no skin to animate"**.
- **Why:** `viewmodel_knife_bowie` is in `nazi_zombie_factory.ff`, but it is a rigid T4 model: one surface, 490 verts, no bones. So `toModelData` makes no skin, and `exportXAnims` rejected any skinless part.
- **Fix (tree, tools/zonedump/ExportAnim.cpp):**
  - a skinless part that's attached to a tag of a model before it now gets `rigidSkin` (one joint of its own under that tag, the helper the t6 attachments already use) and no hit boxes, instead of the error;
  - a first model with no skin still errors.
- **Tested:** with a private build, the factory command above now writes the glb (arms + knife under `tag_weapon`), with 3 anims and 0 failed; `viewmodel_zombie_bowie` binds 65 of 69 bones.
