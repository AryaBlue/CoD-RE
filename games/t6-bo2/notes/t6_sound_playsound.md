# T6 Zombies — `playsound` / sound-alias play path (t6zm.exe)

Reversed on Plutonium `t6zm.exe` (image base `0x400000`). Goal: find where a sound **alias name**
is resolved to a `snd_alias_list_t`, so a tool DLL can register/inject an alias at runtime (e.g. to give
a ported campaign weapon its fire sound without rebuilding and reloading a sound bank).

## GSC builtin registration
The GSC builtin table registers each entry as `push <id>; push <handler>; push <name>; call <register>`.
The `playsound` entry (inside the registrar at `~0x0058aa68`):

```
0058ab7a  push 0x029a5830            ; builtin id / arg
0058ab7f  push 0x008a6330            ; HANDLER  -> playsound
0058ab84  push 0x00bea3fc            ; "playsound"
0058ab89  call 0x004dc2a0            ; Scr_AddFunction-style registrar
```

- `"playsound"` string: `0x00bea3fc`
- builtin registrar: `0x004dc2a0`
- **`playsound` handler: `0x008a6330`**

## `playsound` handler `0x008a6330`
```
push esi ; push 4 ; call 0x0059a740      ; fetch the calling entity/param (returns eax)
...                                      ; entity self-handling via [eax + ecx*4 + 0x84/0xa4]
mov esi, 0x00c59a6c                      ; default alias string when none resolved
call 0x0044c390                          ; play-request / channel setup (allocs, sets [slot+4]=0xA)
movss xmm0,[0x00bfdd24] ...              ; volume / falloff floats, flags 0x00080fff
call 0x004f4380                          ; play the alias at the entity
ret
```

## Play-by-name `0x004f4380`
```
call 0x0063d5a0 ; test eax ; je ret      ; "is the sound system up?" guard
... assemble (origin, flags 0x80fff, 3 zero args, volume floats) ...
call 0x00539e50                          ; <-- core play-by-name; alias hash + lookup lives here
mov edi, eax
call 0x00913800                          ; post-play bookkeeping
ret
```

## Current frontier / injection point
The alias **name → `snd_alias_list_t`** resolution is inside **`0x00539e50`** (next to reverse).
In T6 a sound alias is an XAsset (`ASSET_TYPE_SOUND`, a `snd_alias_list_t`) resolved by hashed name,
so two viable runtime-injection strategies for a tool DLL:

1. **Register a `sound` XAsset** at runtime: build a `snd_alias_list_t` (+ its `snd_alias_t[1]`) that
   points at an already-loaded sound (a loaded_sound XAsset, or an existing streamed entry) and add it
   to the sound-alias hashtable the way a loaded bank would. Resolve the hashtable/registration from
   inside `0x00539e50`.
2. **Load the owning bank**: trigger a load of the bank that already defines the alias
   (e.g. `so_rts_afghanistan.all` `.sabl`/`.sabs`, which defines `wpn_metalstormsnp_fire_plr_1`/`_npc`)
   so zombies gains the aliases without per-alias struct work.

Helper addresses seen on this path: entity/param fetch `0x0059a740`, request/channel setup `0x0044c390`
(calls `0x004f7490`), sound-system-up guard `0x0063d5a0`.

Related: [t6_cbuf.md](t6_cbuf.md) (Cbuf_AddText), [t6_sv_sendservercommand.md](t6_sv_sendservercommand.md).
