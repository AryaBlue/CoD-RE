# MP front end: WaW (T4) and BO1 (T5) create-a-class, default classes and emblems

This covers the data a Play / Weapons / Operator / Barracks front end needs: create-a-class slot rules, perk tiers,
attachments and unlocks, the default classes, and what BO1's emblem editor allows. It is the companion to
[mp_t4_tdm_ffa.md](../../../games/t4-waw/notes/e115/mp_t4_tdm_ffa.md) (match rules).

Tags:
- **[V]**: read in the game files, with a table or script and line.
- **[M]**: measured in game. Nothing in this doc is [M] yet.
- **[I]**: inferred. Treat it as a guess until checked.

Sources:
- **WaW tables:** `mp/statstable.csv`, `mp/ranktable.csv`, `mp/classtable.csv`, `mp/attachmenttable.csv`, from
  `code_post_gfx_mp.ff`.
- **WaW scripts:** `maps/mp/gametypes/_class.gsc`, from `common_mp.ff`.
- **BO1 tables:** `mp/statstable.csv`, `mp/ranktable.csv`, `mp/attachmenttable.csv`, `mp/weaponoptions.csv`,
  `mp/classbonustable.csv`, from `code_post_gfx_mp.ff`.
- **BO1 scripts:** `_class.gsc`, from `common_mp.ff`.
- **BO1 emblem strings:** `patch_ui_mp.ff` and `code_post_gfx_mp.ff`.
- Everything was dumped with OAT to scratch, outside the repo. No assets or script text are copied here: lists and
  numbers only.
- **The menu files can't be read yet.** OAT doesn't dump T4/T5 menus, so screen layouts are not covered. The BO1 menu
  command strings quoted in §3 come from a raw string scan of `patch_ui_mp.ff`.

Notation used in the tables:
- **Unlock level** is the ranktable row + 1. ranktable row 3 (`pfc1`) unlocks `type99rifle`, `bar` and
  `specialty_armorvest`, which statstable labels `PERKS_UNLOCKED_AT_LV4`, so row + 1 = level [V].
- **"start"** means the item has no unlock row, so it is available from the start.

## 1. World at War

### Slots [V] (`_class.gsc:470-646`, `classtable.csv`)

There are 5 custom classes, plus 5 prestige classes once prestiged (`cac_getdata` `:444-464`, stats 200+ and 1200+).
Each class is a block of 10 stats, plus specialty 4 at +105:

| stat | slot | rule |
|---|---|---|
| +0 | primary grenade | statstable 100-109. Anything else becomes the frag. Always 1 (`:514-522`) |
| +1 | primary weapon | anything invalid falls back to the SVT-40 (`:524-534`) |
| +2 | primary attachment | an index into that weapon's attachment list (statstable columns 12-15) |
| +3 / +4 | secondary weapon and its attachment | **must be a pistol unless perk 2 is Overkill** (`:544-552`) |
| +5 / +6 / +7 | perks 1 / 2 / 3 | each must be in that slot's allowed list, or it becomes "none" (`validatePerk` `:665-675`) |
| +105 | perk 4 (vehicle) | same check |
| +8 | special grenade | the count comes from classtable column 6: 1, or 3 with "Special Grenades ×3" |
| +9 | camo | an index into the camo rows of attachmenttable (bitmask). Invalid becomes none (`:505-511`) |

**Allowed perks per slot** [V] (`:373-421`):
- **Perk 1** also holds the attachment placeholders: rows 190-193 are none, grenade launcher, grip and attachment. A
  rifle grenade or grip **uses up perk 1**.
- **Perk 1 inventory items** replace a perk: satchel ×2, betty ×2, bazooka ×2, flamethrower. So do the grenade upgrades,
  frag ×2 and special ×3.
- **Perk 4 is vehicle-only:** Water Cooler, Greased Bearings, Ordinance, Boost, Leadfoot.

### Weapons [V] (`statstable.csv` rows 0-109, unlocks from `ranktable.csv` columns 8-9)

| group | weapon | attachments | unlock level |
|---|---|---|---|
| pistol | `colt` | - | start |
| pistol | `nambu` | - | start |
| pistol | `walther` | - | start |
| pistol | `tokarev` | - | 21 |
| pistol | `357magnum` | - | 49 |
| smg | `thompson` | silenced aperture bigammo | start |
| smg | `mp40` | silenced aperture bigammo | 10 |
| smg | `type100smg` | silenced aperture bigammo | 25 |
| smg | `ppsh` | aperture bigammo | 53 |
| assault | `svt40` | flash aperture telescopic | start |
| assault | `gewehr43` | silenced aperture telescopic gl | 7 |
| assault | `m1garand` | flash bayonet gl scoped | 17 |
| assault | `m1carbine` | flash aperture bayonet bigammo | 65 |
| assault | `stg44` | flash aperture telescopic | 37 |
| hmg | `30cal` | bipod | 61 |
| hmg | `mg42` | bipod | 33 |
| hmg | `dp28` | bipod | 13 |
| projectile | `m2_flamethrower` | - | 65 (as the perk-1 item) |
| projectile | `bazooka` | - | start (as the perk-1 item) |
| sniper | `springfield` | scoped bayonet gl | start |
| sniper | `mosinrifle` | scoped bayonet gl | 21 |
| sniper | `type99rifle` | scoped bayonet gl | 4 |
| sniper | `kar98k` | scoped bayonet gl | 41 |
| sniper | `ptrs41` | - | 57 |
| shotgun | `shotgun` | grip bayonet | start |
| shotgun | `doublebarreledshotgun` | grip sawoff | 29 |
| lmg | `type99lmg` | bipod bayonet | start |
| lmg | `fg42` | bipod telescopic | 45 |
| lmg | `bar` | bipod | 4 |
| lmg | `dp28` | bipod | 13 |
| explosive | `mine_bouncing_betty` | - | 24 (as the perk-1 item) |
| explosive | `satchel_charge` | - | start (as the perk-1 item) |
| grenade | `frag_grenade` | - | start |
| grenade | `molotov` | - | 10 |
| grenade | `m8_white_smoke` | - | start |
| grenade | `tabun_gas` | - | start |
| grenade | `sticky_grenade` | - | start |
| grenade | `signal_flare` | - | start |

Notes:
- The DP-28 has two statstable rows, 42 (hmg) and 83 (lmg).
- Weapon unlocks come with the matching marksman and expert challenges (ranktable column 10).
- **Attachments** [V] (`attachmenttable.csv`): scoped, aperture, silenced, grip, gl (rifle grenade), comp, bigammo,
  flash, bipod, sawoff, bayonet, telescopic and selectfire. Each has a bit, 1 << n.
  - **Only one attachment is allowed per weapon.** The class has one primary attachment stat.
  - Attachment unlocks come from the weapon's challenges [I: the challenge tiers weren't traced].
- **Camos** [V]: none, then Reich, Siberian, Royal, Yankee and Rising Sun (each for "complete the expert challenge"),
  Golden ("unlock everything") and Prestige.

### Perks [V] (`statstable.csv` rows 150-189)

| tier | perk | ref | unlock level |
|---|---|---|---|
| perk1 | Bomb Squad | `specialty_detectexplosive` | 16 |
| perk1 | Bandolier | `specialty_extraammo` | 40 |
| perk2 | Uav Jammer | `specialty_gpsjammer` | 12 |
| perk2 | Sonic Boom | `specialty_explosivedamage` | start |
| perk2 | Flak Jacket | `specialty_flakjacket` | start |
| perk2 | Stopping Power | `specialty_bulletdamage` | start |
| perk2 | Double Tap | `specialty_rof` | 36 |
| perk2 | Sleight Of Hand | `specialty_fastreload` | 28 |
| perk2 | Overkill | `specialty_twoprimaries` | 56 |
| perk2 | Juggernaut | `specialty_armorvest` | 4 |
| perk3 | Tossback | `specialty_pin_back` | 6 |
| perk2 | Shades | `specialty_shades` | 32 |
| perk2 | Gasmask | `specialty_gas_mask` | start |
| perk3 | Iron Lungs | `specialty_holdbreath` | 60 |
| perk3 | Dead Silence | `specialty_quieter` | 52 |
| perk3 | Extreme Conditioning | `specialty_longersprint` | start |
| perk3 | Last Stand | `specialty_pistoldeath` | 9 |
| perk3 | Martyrdom | `specialty_grenadepulldeath` | 20 |
| perk3 | Deep Impact | `specialty_bulletpenetration` | start |
| perk3 | Steady Aim | `specialty_bulletaccuracy` | start |
| perk3 | Fireproof | `specialty_fireproof` | 48 |
| perk3 | Reconnaissance | `specialty_reconnaissance` | 64 |
| perk4 | Greased Bearings | `specialty_greased_barrings` | start |
| perk4 | Water Cooler | `specialty_water_cooled` | start |
| perk4 | Ordinance | `specialty_ordinance` | 12 |
| perk4 | Leadfoot | `specialty_leadfoot` | 28 |
| perk4 | Boost | `specialty_boost` | 40 |
| perk1 | Primary Grenades X 2 | `specialty_fraggrenade` | 44 |
| perk1 | Special Grenades X 3 | `specialty_specialgrenade` | start |
| perk1 | Satchel Charge X 2 | `specialty_weapon_satchel_charge` | start |
| perk1 | Betty X 2 | `specialty_weapon_bouncing_betty` | 24 |
| perk1 | Bazooka X 2 | `specialty_weapon_bazooka` | start |
| perk1 | Flamethrower | `specialty_weapon_flamethrower` | 65 |

Perk numbers (bullet damage +40 %, armour vest 75 %, and so on) are in `_class.gsc:1148-1153`.

### Default classes [V] (`classtable.csv`, loaded at `_class.gsc:131-135`)

| class | primary | secondary | perk 1 | perk 2 | perk 3 | perk 4 | grenades |
|---|---|---|---|---|---|---|---|
| Assault (`CLASS_ASSAULT`, the online default) | SVT-40 | Colt | Satchel ×2 | Stopping Power | Extreme Conditioning | Water Cooler | frag 1, signal flare 1 |
| Spec Ops | Thompson | Colt | Special Grenades ×3 | Gas Mask | Steady Aim | Water Cooler | frag 1, flare 3 |
| Heavy Gunner | Type 99 LMG | Nambu | Special Grenades ×3 | Flak Jacket | Deep Impact | Water Cooler | frag 1, tabun 3 |
| Demolitions | Shotgun | Walther | Bazooka ×2 | Sonic Boom | Extreme Conditioning | Greased Bearings | sticky 1, tabun 1 |
| Sniper | Springfield, scoped | Colt | Satchel ×2 | Stopping Power | Deep Impact | Water Cooler | frag 1, smoke 1 |

- Classtable columns 13 and 14 give alternative primaries (`classWeapons[team][class][1..2]`, `:217-218`). Assault
  has M1 Carbine / SVT-40, and Heavy Gunner has Type 99 / FG42. They are chosen through `pers["primary"]` (`:950-961`).
- The same classtable rows seed the 5 custom slots and the 5 prestige slots.
- Offline (splitscreen and bots) uses 11 classes from `mp/offline_classtable.csv` (`:115-127`) [V for the loader; the
  table wasn't read].
- **Unlocks:** create-a-class at level 4 (ranktable row 3, `feature_cac`). The close assault and sniper classes come at
  levels 2 and 3. Max rank is 65 (`maxrank` 64).

## 2. Black Ops

### Slots [V] (`classbonustable.csv` header, `_class.gsc:209-300`)

A class holds:
- **body and head:** the body follows the tier-1 perk, the head is face paint
- **primary**, with attachment top / bottom / trigger / muzzle, camo, reticle and lens
- **secondary**, with the same set
- **primary grenade** (lethal), **special grenade** (tactical), **equipment**
- **perks 1, 2 and 3**

Killstreaks are chosen separately (`_hardpoints.gsc` `registerKillstreak`, see the match doc §7).

Rules:
- **One attachment** unless perk 2 is **Professional (Warlord)** (`specialty_twoattach`). Its pro version adds
  `specialty_twogrenades` [V, statstable row 168-169].
- Each attachment has a mount (top / bottom / trigger / muzzle) and a list of attachments it can pair with
  (attachmenttable column 11). [I] With Warlord, the second attachment must be in the first one's list and on another
  mount.
- **Every perk has a Pro version.** It adds specialties (statstable rows 151-179) and costs 3000. It is unlocked by the
  perk's challenges [I: the challenge rows weren't traced].
- Items can be excluded by dvar: `item_exclusion_N` and `attachment_exclusion_N` (`_class.gsc:160-200`).
- **The body model depends on perk 1:**

  | tier-1 perk | body |
  |---|---|
  | Lightweight | `standard_mp` |
  | Scavenger | `utility_mp` |
  | Ghost | `camo_mp` |
  | Flak Jacket | `ordnance_disposal_mp` |
  | Hardline | `hardened_mp` |

  [V, statstable rows 97-102]

### Weapons and equipment [V] (`statstable.csv`)

- **Unlock level** is statstable column 10 + 1. The `feature_cac` row has 3, so create-a-class is level 4.
- **CoD Points** are column 12. "default" means the item is in a default class and free.

| slot | group | weapon | attachments | unlock level | CoD Points |
|---|---|---|---|---|---|
| secondary | pistol | `asp` | dw | 4 | default |
| secondary | pistol | `cz75` ¹| upgradesight extclip dw silencer auto | - | 1500 |
| secondary | pistol | `m1911` | upgradesight extclip dw silencer | 4 | default |
| secondary | pistol | `makarov` | upgradesight extclip dw silencer | 4 | default |
| secondary | pistol | `python` | acog snub speed dw | 18 | 1500 |
| primary | smg | `ak74u` | extclip dualclip acog elbit reflex grip silencer gl rf | 17 | 2000 |
| primary | smg | `kiparis` ¹| extclip acog elbit reflex grip dw silencer rf | - | 2000 |
| primary | smg | `mac11` | extclip elbit reflex grip dw silencer rf | 11 | 2000 |
| primary | smg | `mp5k` | extclip acog elbit reflex silencer rf | 4 | default |
| primary | smg | `mpl` | dualclip acog elbit reflex grip silencer rf | 35 | 2000 |
| primary | smg | `pm63` | extclip grip dw rf | 29 | 2000 |
| primary | smg | `skorpion` | extclip grip dw silencer rf | 7 | 2000 |
| primary | smg | `spectre` | extclip acog elbit reflex grip silencer rf | 41 | 2000 |
| primary | smg | `uzi` | extclip acog elbit reflex grip silencer rf | 23 | 2000 |
| primary | assault | `ak47` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 38 | 2000 |
| primary | assault | `aug` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 26 | 2000 |
| primary | assault | `commando` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 44 | 2000 |
| primary | assault | `enfield` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 5 | 2000 |
| primary | assault | `famas` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 14 | 2000 |
| primary | assault | `fnfal` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 32 | 2000 |
| primary | assault | `g11` ¹| lps vzoom | - | 2000 |
| primary | assault | `galil` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 20 | 2000 |
| primary | assault | `m14` | extclip acog elbit reflex grip mk ft ir silencer gl | 9 | 2000 |
| primary | assault | `m16` | extclip dualclip acog elbit reflex mk ft ir silencer gl | 4 | default |
| primary | lmg | `hk21` | extclip acog elbit reflex ir | 4 | default |
| primary | lmg | `m60` | extclip acog elbit reflex grip ir | 21 | 2000 |
| primary | lmg | `rpk` | extclip dualclip acog elbit reflex ir | 6 | 2000 |
| primary | lmg | `stoner63` ¹| acog elbit extclip ir reflex | - | 2000 |
| primary | sniper | `dragunov` | extclip acog ir silencer vzoom | 4 | default |
| primary | sniper | `l96a1` | extclip acog ir silencer vzoom | 27 | 2000 |
| primary | sniper | `psg1` ¹| extclip acog ir silencer vzoom | - | 2000 |
| primary | sniper | `wa2000` | extclip acog ir silencer vzoom | 10 | 2000 |
| primary | cqb | `hs10` ¹| dw | - | 2000 |
| primary | cqb | `ithaca` | grip | 8 | 2000 |
| primary | cqb | `rottweil72` | - | 4 | default |
| primary | cqb | `spas` | silencer | 24 | 2000 |
| secondary | launcher | `m72_law` | - | 4 | default |
| secondary | launcher | `rpg` | - | 12 | 2000 |
| secondary | launcher | `strela` | - | 30 | 2000 |
| secondary | special | `crossbow_explosive` | - | 33 | 2000 |
| secondary | launcher | `china_lake` | - | 48 | 2000 |
| secondary | special | `knife_ballistic` | - | 15 | 1500 |
| primarygrenade | grenade | `frag_grenade` | - | 4 | default |
| primarygrenade | grenade | `sticky_grenade` | - | 4 | 2000 |
| primarygrenade | grenade | `hatchet` | - | 4 | 2000 |
| specialgrenade | grenade | `willy_pete` | - | 4 | default |
| specialgrenade | grenade | `tabun_gas` | - | 4 | 1500 |
| specialgrenade | grenade | `flash_grenade` | - | 4 | 1500 |
| specialgrenade | grenade | `concussion_grenade` | - | 4 | 1500 |
| specialgrenade | grenade | `nightingale` | - | 4 | 1500 |
| equipment | explosive | `claymore` | - | 4 | 5000 |
| equipment | explosive | `satchel_charge` | - | 4 | 2000 |
| equipment | grenade | `scrambler` | - | 4 | 2500 |
| equipment | grenade | `tactical_insertion` | - | 4 | 2500 |
| equipment | grenade | `camera_spike` | - | 4 | 2000 |
| equipment | grenade | `acoustic_sensor` | - | 4 | 5000 |

- ¹ These rows have no unlock rank. Column 15 holds 4 / 8 / 9 / 3 / 3 / 3 [I: meaning unknown, possibly a later or
  conditional unlock].
- Dual wield (`*dw`) is the `dw` attachment, not a separate pick.
- Camos (`weaponoptions.csv`): 15 camos at 250 each, plus gold. Lenses: white, red and blue. Reticles unlock at
  level 25.

**Attachments** [V] (`attachmenttable.csv`):

| attachment | mount | CoD Points | can pair with (Warlord) |
|---|---|---|---|
| reflex | top | 1000 | dualclip extclip grip rf silencer |
| elbit | top | 1000 | dualclip extclip grip rf silencer |
| acog | top | 1000 | dualclip extclip grip rf silencer |
| lps | top | 2000 | - |
| vzoom | top | 2000 | extclip silencer |
| ir | top | 2000 | dualclip extclip grip silencer |
| gl | bottom | 3000 | - |
| mk | bottom | 1000 | - |
| silencer | muzzle | 2000 | acog dualclip elbit extclip grip ir reflex rf upgradesight vzoom |
| grip | bottom | 1000 | acog dualclip elbit extclip ir reflex rf silencer |
| extclip | trigger | 1000 | acog elbit grip ir reflex rf silencer upgradesight vzoom |
| dualclip | trigger | 1000 | acog elbit grip ir reflex rf silencer |
| rf | trigger | 3000 | acog dualclip elbit extclip grip reflex silencer |
| ft | bottom | 1000 | - |
| auto | trigger | 2000 | - |
| speed | trigger | 1000 | - |
| upgradesight | top | 250 | - |
| snub | muzzle | 500 | - |
| dw | bottom | 1000 | - |

### Perks [V]

| tier | perk | unlock level | CoD Points |
|---|---|---|---|
| 1 | Lightweight | 4 | default |
| 1 | Lightweight Pro | pro (challenges) | 3000 |
| 1 | Scavenger | 4 | 2000 |
| 1 | Scavenger Pro | pro (challenges) | 3000 |
| 1 | Ghost | 4 | 2000 |
| 1 | Ghost Pro | pro (challenges) | 3000 |
| 1 | Flak Jacket | 4 | 2000 |
| 1 | Flak Jacket Pro | pro (challenges) | 3000 |
| 1 | Hardline | 4 | 2000 |
| 1 | Hardline Pro | pro (challenges) | 3000 |
| 2 | Steady Aim | 4 | 2000 |
| 2 | Steady Aim Pro | pro (challenges) | 3000 |
| 2 | Scout | 4 | 2000 |
| 2 | Scout Pro | pro (challenges) | 3000 |
| 2 | Deep Impact | 4 | default |
| 2 | Deep Impact Pro | pro (challenges) | 3000 |
| 2 | Sleight Of Hand | 4 | 2000 |
| 2 | Sleight Of Hand Pro | pro (challenges) | 3000 |
| 2 | Professional (Warlord) | 4 | 2000 |
| 2 | Professional (Warlord) Pro | pro (challenges) | 3000 |
| 3 | Marathon | 4 | 2000 |
| 3 | Marathon Pro | pro (challenges) | 3000 |
| 3 | Ninja | 4 | 2000 |
| 3 | Ninja Pro | pro (challenges) | 3000 |
| 3 | Second Chance | 4 | 2000 |
| 3 | Second Chance Pro | pro (challenges) | 3000 |
| 3 | Hacker | 4 | 2000 |
| 3 | Hacker Pro | pro (challenges) | 3000 |
| 3 | Tactical Mask | 4 | default |
| 3 | Tactical Mask Pro | pro (challenges) | 3000 |

### Killstreaks [V] (`statstable.csv` column 5 = kills)

| streak | kills | unlock level | CoD Points |
|---|---|---|---|
| Recon | 3 | - | default |
| Supply Drop | 5 | - | default |
| Rcbomb | 3 | - | 1200 |
| Auto Turret Drop | 6 | - | 3200 |
| Tow Turret Drop | 4 | - | 1600 |
| Mortar | 6 | - | 3200 |
| Napalm | 5 | - | 2400 |
| Satellite | 8 | - | 4500 |
| Helicopter Comlink | 7 | - | default |
| Helicopter Gunner | 9 | - | 5000 |
| Counter Uav | 4 | - | 1600 |
| Airstrike | 8 | - | 4500 |
| Helicopter Player | 11 | - | 6000 |
| Dogs | 11 | - | 6000 |
| M220 Tow Drop | 7 | - | 4000 |

- "default" means the streak is in every class (`all`).
- Killstreak selection unlocks at level 10.
- Rows with no kill count (Auto Turret, TOW Turret, Minigun, M220 TOW, M202) are the deployed or carried forms of a
  streak.

### Feature unlocks [V] (`statstable.csv` rows 216-244)

feature_killstreaks: level 10
feature_contracts: level 5
feature_reticles: level 25
feature_lenses: level 28
feature_gun_tag: level 19
feature_gun_emblem: level 16
feature_facepaint: level 31
feature_second_attachment: level -
feature_emblem: level 10
feature_closeassault: level 2
feature_sniper: level 3
feature_cac: level 4
feature_camo: level 22
feature_combat_record: level 13
feature_clantag: level 6
feature_prestige_lb: level -, prestige 1, cost 50000
feature_challenges: level 4
feature_challenges_specials: level 15
feature_prestige_class1: level -, prestige 1
feature_prestige_class2: level -, prestige 3
feature_prestige_class3: level -, prestige 5
feature_prestige_class4: level -, prestige 7
feature_prestige_class5: level -, prestige 9
feature_reticle_color: level 25
feature_challenges_killstreaks: level 10
feature_challenges_elite: level 20
feature_challenges_final: level 30
feature_challenges_gamemode: level 8
feature_challenges_medals: level 15

- Max rank is 50 (`maxrank` 49).
- The 5 prestige classes open at prestige 1, 3, 5, 7 and 9.

### Default classes [V] (`statstable.csv` class tags, read by the engine `GetDefaultClassSlot`, `_class.gsc:105-109`)

| class | primary | secondary | lethal | tactical | perk 1 | perk 2 | perk 3 |
|---|---|---|---|---|---|---|---|
| Assault | M16 | ASP | frag | flashbang | Scavenger | Steady Aim | Second Chance |
| SMG | MP5K | ASP | frag | flashbang | Lightweight | Steady Aim | Marathon |
| CQB | Olympia (`rottweil72`) | M1911 | Semtex (`sticky_grenade`) | concussion | Hardline | Sleight of Hand | Tactical Mask |
| LMG | HK21 | M72 LAW | Semtex | concussion | Flak Jacket | Deep Impact | Hacker |
| Sniper | Dragunov | Makarov | frag | Willy Pete | Ghost | Scout | Ninja |

- Custom slots start from the `class_custom_*` tags: that class's guns, frag, Willy Pete, Lightweight, Deep Impact and
  Tactical Mask.
- No default class has equipment (none is tagged).
- Recon and Supply Drop are in every class [V, column 11 `all`], and so is Attack Helicopter.

## 3. BO1 emblem editor

What the files show [V]:
- **Backgrounds:** 198 `emblem_bg_*` materials in `code_post_gfx_mp.ff` (200 `emblem*` materials, minus the two colour
  LUTs). They include flags, camo, zombies, wager and DLC.
- **Colour:** materials `emblem_lut` and `emblem_lut_2d`. [I] The colour picker samples a LUT texture, so layer colours
  are a continuous range, not a fixed palette.
- **Stats layout** (the DDL names in `code_post_gfx_mp.ff`):
  - `emblemstats_s` with `backgrounds`, `icons`, `layers` and `layerspurchased`
  - `emblemicon_s` with `unlocked` and `timespurchased`
  - `emblemlayer_s`
- **Menu commands** (`patch_ui_mp.ff`):
  - `emblemIcon(id)`, `emblemClear`, `emblemselectbackground(i)`
  - `emblempurchaseicon(id)`, `emblempurchasebackgroundbyindex(i)`, `emblempurchaselayer`
  - menus `emblem_edit`, `emblem_icon_select`, `emblem_bg_select`
  - confirmation dialogs to buy a layer, an icon or a background, with CoD Points
- **So icons (decals), backgrounds and extra layers are each bought separately.** Global counters
  `global_emblem_created`, `global_emblem_imagespurchased` and `global_emblem_layerspurchased`.
- **Unlocks:** the player emblem at level 10 (`feature_emblem`) and the gun emblem at level 16 (`feature_gun_emblem`).
  There are also clan tags at 6 and gun tags at 19.

Not found in the files [I], from general knowledge:
- **Layer limits:** 4 layers to start, buy up to 12. The DDL array sizes weren't decoded.
- **Per layer:** one decal, with move, scale, rotate, flip, colour and alpha.
- **Decal count:** a few hundred icons. Their materials aren't in `code_post_gfx_mp`, possibly in `frontend.ff`.

To make these [V]:
- Decode the T5 DDL binary (`emblemstats_s` array sizes).
- Or read the `emblem_edit` menu with a T5 menu parser. Ate47's ACTS may handle T5 menus and DDL [I].

## Open items

- Menu layouts for Play / Weapons / Operator / Barracks: no T4/T5 menu dumper. The candidates are an ACTS check, or
  in-game GPU readback screenshots [M].
- The BO1 emblem layer and decal limits (above).
- The six BO1 weapons with no unlock rank (¹).
- WaW and BO1 attachment / Pro unlock challenges (the challenge tables are dumped but not read).
- WaW `offline_classtable.csv` contents.
