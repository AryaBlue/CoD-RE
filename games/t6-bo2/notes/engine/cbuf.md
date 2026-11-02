# T6 Zombies (Plutonium t6zm.exe) - Cbuf_AddText

Reversed 2026-10-19 from `%LOCALAPPDATA%\Plutonium\games\t6zm.exe` on disk (image base 0x400000).
Dedicated-server map (`pc pdb\CoDMPServer_PC.map`): `?Cbuf_AddText@@YAXW4LocalClientNum_t@@PBD@Z` at 0x006B1A90.

| what | t6zm address |
|---|---|
| `void __cdecl Cbuf_AddText(LocalClientNum_t localClientNum, const char *text)` | 0x006B9D20 |
| `Cbuf_Init` | 0x004B9070 |
| `Sys_EnterCriticalSection(CriticalSection)` -> KERNEL32 EnterCriticalSection | 0x0042A630 |
| `Sys_LeaveCriticalSection(CriticalSection)` -> KERNEL32 LeaveCriticalSection | 0x00596EB0 |
| `s_criticalSection` (CRITICAL_SECTION[], 24 bytes each) | 0x02B14EC8 |
| `cmd_textArray[localClientNum]` (12 bytes each) | 0x025321B4 |
| `cmd_textArray[0].data` (64 KB) | 0x0251F8C8 |
| second 64 KB cmd_t (initialised beside it) | 0x0250F8B4, data 0x0250F8C8 |

```c
struct cmd_t { char *data; int maxsize; int cursize; };   // Cbuf_Init: data, 0x10000, 0

void Cbuf_AddText(LocalClientNum_t lc, const char *text)
{
    Sys_EnterCriticalSection(CRITSECT_CBUF);            // 0x33
    if (text && (text[0] == 'p' || text[0] == 'P') && text[1] == '0')
        text += 2;                                      // "p0" (local client 0) prefix dropped
        // (the compiled check of the following space tests text[0] and ends in an
        //  unreachable `jmp $`; in effect any "p0"/"P0" start loses two characters)
    cmd_t *cmd = &cmd_textArray[lc];
    int len = strlen(text);
    if (cmd->cursize + len >= cmd->maxsize) {           // overflow: dropped silently in this
        Sys_LeaveCriticalSection(CRITSECT_CBUF);        // build (the "Cbuf_AddText: overflow"
        return;                                         // string is unused here)
    }
    memcpy(cmd->data + cmd->cursize, text, len + 1);    // copies the NUL ...
    cmd->cursize += len;                                // ... but does not count it
    Sys_LeaveCriticalSection(CRITSECT_CBUF);
}
```

Notes: it only queues - commands run on the main thread at the next `Cbuf_Execute`; text needs its own
trailing `\n`; safe to call from another thread (critical section 0x33). Plutonium may hook the running
image; this is the on-disk code.
