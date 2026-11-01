# BO1 sound alias volume groups

Found 2026-11-01 while matching in-game levels (zonedump `Sound.cpp`). Tags: **[V]** read in data, **[M]** measured on
Kino der Toten, **[I]** inferred.

- Every BO1 sound alias has a volume group. The group index is in bits 16-21 of the alias flags **[V]**.
- The zone's sound-driver globals asset holds the group table. Each group has a name, a parent index and a per-mode
  attenuation (the single-player column is the one we use, stored as a u16 where 65535 is 1.0).
- The mixed volume is the alias volume times the group's attenuation, times its parent's, and so on up to the master
  group **[I]**: chained as the parent index says; we cap the walk at 8 hops.
- Examples from Kino **[M]**: player weapon aliases sit in the `wpn_*_plr` groups, music is group 5, UI is 18, ambience
  is 14.
- If you skip this, weapon and ambience levels come out wrong against the game, because the alias volume alone ignores
  the mix.

Related: [audio.md](../../../../shared/notes/e115/audio.md) for the alias record and playback rules.
