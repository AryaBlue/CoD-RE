# BO2 zombies round number font

Which font asset the zombies HUD's round number uses, and whether PC has it. Marks are explained in the
[E115 notes index](../../../shared/notes/e115/README.md).

## Where the font is chosen

- [V] The round counter widget in the zombies HUD script sets `CoD.fonts["Morris"]`.
- [V] Neither the 360 `CoDMP` nor `CoDSP` binary contains "Morris", a `CoD.fonts` table or any font family name.
  `RegisterFont` is only reachable from Lua. The only font asset paths hard-coded in the exe are the dev fonts
  (`fonts/smallDevFont`, `fonts/bigDevFont`), `fonts/distfont` and `fonts/720/consolefont`.
- [V] `CoD.fonts` is built by the base LUI script `ui/t6/codbase.lua`, which on PC ships in `patch_zm.ff` as
  HavokScript bytecode. Each font is registered from `"fonts/" .. <r_fontResolution dvar> .. "/<name>"`, plus
  `fonts/distFont` for `Dist`.

## The mapping

- [I] Read from the order of the bytecode's string constants (keys and paths enter the constant table in source
  order), not instruction by instruction. For the non-Asian branch:

| `CoD.fonts` key | Font file |
| --- | --- |
| Condensed | normalFont |
| Default | smallFont |
| Big | bigFont |
| **Morris** | **extraBigFont** |
| ExtraSmall | extraSmallFont |
| Italic | italicFont |
| SmallItalic | smallItalicFont |

- [I] An earlier branch on the `loc_language` dvar maps most keys to `normalFont` instead (Asian languages).
- [V] PC ships `fonts/720/extraBigFont` (in `en_code_post_gfx.ff` and `en_code_post_gfx_zm.ff`, alongside big, small,
  smallItalic, italic, bold, normal, extraSmall and console). So on PC the round number is drawn with
  `fonts/720/extraBigFont`.

## Credits

OpenAssetTools' Unlinker to list and dump the zones; ate47's atian-cod-tools `luad` was tried on the bytecode but
stopped on an unknown constant type. The zones are the user's own install; no script text is reproduced.
