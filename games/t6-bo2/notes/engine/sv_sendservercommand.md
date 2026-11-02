# T6 Zombies (Plutonium t6zm.exe) - SV_SendServerCommand

Reversed 2026-10-19 from `%LOCALAPPDATA%\Plutonium\games\t6zm.exe` on disk (image base 0x400000). Located through
`SV_AddServerCommand` (only user of "EXE_SERVERCOMMANDOVERFLOW" outside its inlined copy). Server map names:
`?SV_SendServerCommand@@YAXPAUclient_t@@W4svscmd_type@@PBDZZ` 0x006F05B0, `SV_AddServerCommand` 0x006F0370.

```c
enum svscmd_type { SV_CMD_CAN_IGNORE = 0, SV_CMD_RELIABLE = 1 };
typedef void (__cdecl *SV_SendServerCommand_t)(client_t *cl, svscmd_type type, const char *fmt, ...);
SV_SendServerCommand_t SV_SendServerCommand = (SV_SendServerCommand_t)0x005F4F10;
```

| what | t6zm |
|---|---|
| SV_SendServerCommand | 0x005F4F10 |
| SV_AddServerCommand(client_t*, svscmd_type, const char*) | 0x005828C0 |
| SV_CanReplaceServerCommand(client_t*, const char*) -> index or -1 | 0x008921E0 |
| SV_CullIgnorableServerCommands (client_t* in edx) | 0x00892300 |
| MSG_WriteReliableCommandToBuffer(src, &dst, buffer, 0x4000, &pos) | 0x0048E0C0 |
| SV_DropClient(client_t*, reason) | 0x005EBF70 |
| NET_OutOfBandPrint(4 = NS_SERVER, netadr_t by value, "disconnect") | 0x004058C0 |
| va | 0x0044A120 |
| Dvar_GetInt/Bool (dvar_t*) | 0x006909F0 |
| _vsnprintf | 0x00A6CEAF |
| static message buffer (64 KB) | 0x028DC200 |
| svs.clients (client_t*, 0x4E180 bytes each) | *(0x028EC9C0) |
| svs.time | 0x028EC9B0 |
| sv_maxclients (dvar_t*) | *(0x025B60E4) |

```c
void SV_SendServerCommand(client_t *cl, svscmd_type type, const char *fmt, ...)
{
    static char message[0x10000];                       // 0x028DC200
    va_list ap; va_start(ap, fmt);
    _vsnprintf(message, sizeof(message), fmt, ap);      // no forced terminator

    if (cl) { SV_AddServerCommand(cl, type, message); return; }

    if (Dvar_GetBool(*(dvar_t **)0x02534740))           // com_dedicated-like
        I_strncmp(message, "print", 5);                 // "broadcast: %s" print stripped: result unused

    client_t *c = svs.clients;
    for (int i = Dvar_GetInt(sv_maxclients); i > 0; --i, ++c) {
        if (c->state < 4) continue;                     // only loading/active clients
        SV_AddServerCommand(c, type, message);          // inlined, see below
    }
}

// SV_AddServerCommand (inlined copy; field names from offsets)
//   client_t +0x0000 state, +0x0028 netadr_t (20 bytes), +0x0B30 char reliableBuffer[0x4000],
//   +0x4B30 int reliableBufferPos, +0x4B34 { char *cmd; int time; int type; } reliableCommandInfo[128],
//   +0x5134 reliableSequence, +0x5138 reliableAcknowledge, +0x4028C flag that skips the overflow
//   checks (likely a bot / local client)
//   - not flagged and >= 64 unacked, or not CS_ACTIVE (5): SV_CullIgnorableServerCommands; then
//     SV_CMD_CAN_IGNORE commands are dropped for that client
//   - SV_CanReplaceServerCommand: a matching pending command is removed (ring shifted down),
//     otherwise ++reliableSequence
//   - 129 unacked (not flagged): OOB "disconnect", SV_DropClient(cl, "EXE_SERVERCOMMANDOVERFLOW"),
//     and the queued text becomes va("%c \"EXE_SERVERCOMMANDOVERFLOW\"", '5')
//   - the text goes into the client's 16 KB ring buffer; info[seq & 127] = { ptr, svs.time, type };
//     if the buffer wrapped over a still-unacknowledged command: disconnect + drop as above
```

Notes: the formatted text is limited by the client's 16 KB reliable buffer and 128 pending commands, not the
64 KB format buffer. Broadcasts skip clients below state 4. The function isn't thread-safe (shared static
buffer): call it from the server thread.
