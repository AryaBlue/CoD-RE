// ZM Workshop custom perks - runtime (Plutonium T6 Zombies).
//
// Perks are written in Lua against the API in perks/API.md; lua2gsc compiles each one to GSC and appends it to
// this file, followed by zmwp_register_all(), which calls every perk's register function. Each perk then:
//   - is a virtual perk: owning it is tracked here (player.zmwp_owned), not with an engine specialty, so there is
//     no limit on how many exist. It still counts towards the perk limit (num_perks) and is lost on going down;
//     its `specialties` turn real engine perks on while it is owned;
//   - gets a HUD icon drawn here (stock icons come from client scripts we can't extend);
//   - can be bought from machines placed per map (zmwp_place) or given by the tool (dvar zmw_perk_cmd).
// The tool can also load a perk into a match that is already running: lua2gsc's live bytecode arrives in dvars and
// zmwi_run interprets it (zmwi_* below); the compiled copy takes over at the next map start.
// Only functions every Zombies map has are called (patch_zm), and engine builtins.

#include common_scripts\utility;
#include maps\mp\_utility;
#include maps\mp\zombies\_zm_utility;

main()
{
}

init()
{
    level.zmwp = [];
    level.zmwp_ids = [];
    level.zmwp_shaders = [];
    level.zmwp_models = [];
    level.zmwp_default_icon = "specialty_juggernaut_zombies";
    zmwp_precache_shader( level.zmwp_default_icon );
    zmwi_init();
    zmwp_register_all();
    level.zmwp_cmd_last = getdvar( "zmw_perk_cmd" );
    level thread zmwp_watch_commands();
    // always hooked: a perk can be loaded live later in the match
    maps\mp\zombies\_zm::register_player_damage_callback( ::zmwp_player_damage );
    maps\mp\zombies\_zm_spawner::register_zombie_death_event_callback( ::zmwp_zombie_death );
    level thread zmwp_hook_actor_damage();
    level thread zmwp_connect();
    level thread zmwp_rounds();
    level thread zmwp_spawn_machines();
}

// art can only be precached while the map loads; a perk loaded live later falls back to what is already loaded
zmwp_precache_shader( name )
{
    if ( isdefined( level.zmwp_shaders[name] ) )
        return;

    precacheshader( name );
    level.zmwp_shaders[name] = 1;
}

zmwp_precache_model( name )
{
    if ( isdefined( level.zmwp_models[name] ) )
        return;

    precachemodel( name );
    level.zmwp_models[name] = 1;
}

// Called by each compiled perk's register function.
//   info: struct with id, name, cost, hint, icon, color, machine, bottle, machines, specialties (any may be undefined but id)
//   h:    struct of handler function pointers (give, take, kill, hit, damaged, downed, revived, round, tick, tick_every)
zmwp_add( info, h )
{
    info.handlers = h;

    if ( isdefined( h.tick_every ) )
        info.tick_every = h.tick_every;

    zmwp_defaults( info );
    level.zmwp[info.id] = info;
    level.zmwp_ids[level.zmwp_ids.size] = info.id;
    zmwp_precache_shader( info.icon );

    if ( isdefined( info.machine ) )
        zmwp_precache_model( info.machine );
}

zmwp_defaults( info )
{
    if ( !isdefined( info.name ) )
        info.name = info.id;

    if ( !isdefined( info.cost ) )
        info.cost = 2500;

    if ( !isdefined( info.hint ) )
        info.hint = "Hold ^3[{+activate}]^7 for " + info.name + " [Cost: &&1]";

    if ( !isdefined( info.icon ) )
        info.icon = level.zmwp_default_icon;

    if ( !isdefined( info.tick_every ) )
        info.tick_every = 0.5;
}

zmwp_icon( p )
{
    if ( isdefined( level.zmwp_shaders[p.icon] ) )
        return p.icon;

    return level.zmwp_default_icon;
}

zmwp_bottle( p )
{
    if ( isdefined( p.bottle ) )
        return p.bottle;

    if ( isdefined( level.machine_assets ) && isdefined( level.machine_assets["juggernog"] ) )
        return level.machine_assets["juggernog"].weapon;

    return "zombie_perk_bottle_jugg";
}

// ---------------------------------------------------------------- owning a perk

zmwp_owns( player, p )
{
    return isdefined( player ) && isplayer( player ) && isdefined( player.zmwp_owned ) && isdefined( player.zmwp_owned[p.id] );
}

zmwp_give( player, p, bought )
{
    if ( zmwp_owns( player, p ) )
        return;

    if ( !isdefined( player.zmwp_owned ) )
        player.zmwp_owned = [];

    if ( !isdefined( player.num_perks ) )
        player.num_perks = 0;

    player.zmwp_owned[p.id] = 1;
    player.num_perks++;
    player zmwp_specialties( p, 1 );
    player zmwp_hud_add( p );
    player thread zmwp_tick( p );
    player thread zmwp_watch_loss( p );

    if ( isdefined( bought ) && bought )
        player thread zmwp_bought_fx();

    zmwp_fire( p, "give", player );
    player notify( "perk_acquired" );
}

zmwp_take( player, p )
{
    if ( zmwp_owns( player, p ) )
        player notify( "zmwp_take_" + p.id );
}

zmwp_bought_fx()
{
    self endon( "disconnect" );
    self maps\mp\zombies\_zm_audio::playerexert( "burp" );
    self setblur( 4, 0.1 );
    wait 0.1;
    self setblur( 0, 0.1 );
}

// like _zm_perks' perk_think: the perk goes on going down or dying unless Who's Who keeps the player's perks
zmwp_watch_loss( p )
{
    self endon( "disconnect" );
    stop = "zmwp_take_" + p.id;

    while ( true )
    {
        result = self waittill_any_return( "fake_death", "death", "player_downed", stop );

        if ( result == stop || !( isdefined( self._retain_perks ) && self._retain_perks ) )
            break;
    }

    self.zmwp_owned[p.id] = undefined;
    self.num_perks--;
    self zmwp_specialties( p, 0 );
    self zmwp_hud_remove( p );
    self notify( "zmwp_lost_" + p.id );
    zmwp_fire( p, "take", self );
}

// engine perks a custom perk switches on: counted, so two perks sharing one don't fight; one the player
// also has from its stock machine (perks_active) is left alone
zmwp_specialties( p, on )
{
    if ( !isdefined( p.specialties ) )
        return;

    if ( !isdefined( self.zmwp_spec ) )
        self.zmwp_spec = [];

    foreach ( s in p.specialties )
    {
        if ( !isdefined( self.zmwp_spec[s] ) )
            self.zmwp_spec[s] = 0;

        if ( on )
        {
            if ( self.zmwp_spec[s] == 0 )
                self setperk( s );

            self.zmwp_spec[s]++;
        }
        else if ( self.zmwp_spec[s] > 0 )
        {
            self.zmwp_spec[s]--;

            if ( self.zmwp_spec[s] == 0 && !( isdefined( self.perks_active ) && zmwp_in( self.perks_active, s ) ) )
                self unsetperk( s );
        }
    }
}

// handler f( player ) every p.tick_every seconds while the player has the perk (read each time: a live reload can change it)
zmwp_tick( p )
{
    self endon( "disconnect" );
    self endon( "zmwp_lost_" + p.id );

    while ( true )
    {
        wait( p.tick_every );

        if ( zmwp_has_handler( p, "tick" ) )
            zmwp_fire( p, "tick", self );
    }
}

// ---------------------------------------------------------------- handlers: compiled function pointers or live bytecode

zmwp_has_handler( p, ev )
{
    if ( isdefined( p.live ) )
        return isdefined( p.live.h[ev] );

    return isdefined( zmwp_handler( p, ev ) );
}

zmwp_handler( p, ev )
{
    h = p.handlers;

    if ( !isdefined( h ) )
        return undefined;

    switch ( ev )
    {
        case "give":
            return h.give;
        case "take":
            return h.take;
        case "kill":
            return h.kill;
        case "hit":
            return h.hit;
        case "damaged":
            return h.damaged;
        case "downed":
            return h.downed;
        case "revived":
            return h.revived;
        case "round":
            return h.round;
        case "tick":
            return h.tick;
    }

    return undefined;
}

// each compiled handler is called with exactly the arguments it declares (lua2gsc pads them)
zmwp_fire( p, ev, a, b, c, d, e )
{
    if ( isdefined( p.live ) )
    {
        if ( !isdefined( p.live.h[ev] ) )
            return undefined;

        args = [];
        args[0] = a;
        args[1] = b;
        args[2] = c;
        args[3] = d;
        args[4] = e;
        return zmwi_call( p.live, p.live.h[ev], args );
    }

    f = zmwp_handler( p, ev );

    if ( !isdefined( f ) )
        return undefined;

    switch ( ev )
    {
        case "kill":
            return [[ f ]]( a, b, c, d );
        case "hit":
        case "damaged":
            return [[ f ]]( a, b, c, d, e );
        case "round":
            return [[ f ]]( a, b );
    }

    return [[ f ]]( a );
}

// ---------------------------------------------------------------- events

zmwp_player_damage( einflictor, eattacker, idamage, idflags, smeansofdeath, sweapon, vpoint, vdir, shitloc, psoffsettime )
{
    damage = idamage;
    changed = 0;

    foreach ( id in level.zmwp_ids )
    {
        p = level.zmwp[id];

        if ( zmwp_owns( self, p ) && zmwp_has_handler( p, "damaged" ) )
        {
            result = zmwp_fire( p, "damaged", self, eattacker, damage, smeansofdeath, sweapon );

            if ( isdefined( result ) )
            {
                damage = int( result );
                changed = 1;
            }
        }
    }

    if ( changed )
        return damage;

    return -1;
}

zmwp_hook_actor_damage()
{
    wait 0.05;
    level.zmwp_actor_damage = level.callbackactordamage;
    level.callbackactordamage = ::zmwp_actor_damage;
}

zmwp_actor_damage( inflictor, attacker, damage, flags, meansofdeath, weapon, vpoint, vdir, shitloc, psoffsettime, boneindex )
{
    if ( isdefined( attacker ) && isplayer( attacker ) && isdefined( damage ) && isdefined( attacker.zmwp_owned ) )
    {
        foreach ( id in level.zmwp_ids )
        {
            p = level.zmwp[id];

            if ( zmwp_owns( attacker, p ) && zmwp_has_handler( p, "hit" ) )
            {
                result = zmwp_fire( p, "hit", attacker, self, damage, meansofdeath, weapon );

                if ( isdefined( result ) )
                    damage = int( result );
            }
        }
    }

    self [[ level.zmwp_actor_damage ]]( inflictor, attacker, damage, flags, meansofdeath, weapon, vpoint, vdir, shitloc, psoffsettime, boneindex );
}

// self = the zombie that died
zmwp_zombie_death()
{
    player = self.attacker;

    if ( !isdefined( player ) || !isplayer( player ) || !isdefined( player.zmwp_owned ) )
        return;

    foreach ( id in level.zmwp_ids )
    {
        p = level.zmwp[id];

        if ( zmwp_owns( player, p ) && zmwp_has_handler( p, "kill" ) )
            player thread zmwp_kill_event( p, self, self.damageweapon, self.damagemod );
    }
}

zmwp_kill_event( p, zombie, weapon, means )
{
    zmwp_fire( p, "kill", self, zombie, weapon, means );
}

zmwp_connect()
{
    while ( true )
    {
        level waittill( "connected", player );
        player thread zmwp_player_events();
    }
}

// downed fires before the perks are lost (zmwp_watch_loss waits on the same notify, a frame later in its own thread)
zmwp_player_events()
{
    self endon( "disconnect" );
    self.zmwp_hud = [];

    while ( true )
    {
        event = self waittill_any_return( "player_downed", "player_revived" );
        ev = "revived";

        if ( event == "player_downed" )
            ev = "downed";

        foreach ( id in level.zmwp_ids )
        {
            p = level.zmwp[id];

            if ( zmwp_owns( self, p ) && zmwp_has_handler( p, ev ) )
                self thread zmwp_event_thread( p, ev );
        }
    }
}

zmwp_event_thread( p, ev )
{
    zmwp_fire( p, ev, self );
}

zmwp_rounds()
{
    level endon( "end_game" );

    while ( true )
    {
        level waittill( "start_of_round" );

        foreach ( id in level.zmwp_ids )
        {
            p = level.zmwp[id];

            if ( !zmwp_has_handler( p, "round" ) )
                continue;

            foreach ( player in getplayers() )
            {
                if ( zmwp_owns( player, p ) )
                    player thread zmwp_round_thread( p );
            }
        }
    }
}

zmwp_round_thread( p )
{
    zmwp_fire( p, "round", self, level.round_number );
}

// ---------------------------------------------------------------- HUD: custom icons in rows above the stock ones
// dvar zmw_perk_hud = "x y size gap per_row" moves them (defaults below) without rebuilding.

zmwp_hud_layout()
{
    layout = [];
    layout[0] = 5;
    layout[1] = -110;
    layout[2] = 24;
    layout[3] = 28;
    layout[4] = 12;
    raw = getdvar( "zmw_perk_hud" );

    if ( raw != "" )
    {
        parts = strtok( raw, " " );

        for ( i = 0; i < parts.size && i < 5; i++ )
            layout[i] = int( parts[i] );
    }

    if ( layout[4] < 1 )
        layout[4] = 1;

    return layout;
}

zmwp_hud_add( p )
{
    if ( !isdefined( self.zmwp_hud ) )
        self.zmwp_hud = [];

    hud = newclienthudelem( self );
    hud.horzalign = "user_left";
    hud.vertalign = "user_bottom";
    hud.alignx = "left";
    hud.aligny = "bottom";
    hud.foreground = 1;
    hud.hidewheninmenu = 1;
    hud.alpha = 1;
    self.zmwp_hud[p.id] = hud;
    self zmwp_hud_style( p );
    self zmwp_hud_arrange();
}

zmwp_hud_style( p )
{
    hud = self.zmwp_hud[p.id];

    if ( !isdefined( hud ) )
        return;

    if ( isdefined( p.color ) )
        hud.color = p.color;
    else
        hud.color = ( 1, 1, 1 );

    layout = zmwp_hud_layout();
    hud setshader( zmwp_icon( p ), layout[2], layout[2] );
}

zmwp_hud_remove( p )
{
    if ( isdefined( self.zmwp_hud[p.id] ) )
        self.zmwp_hud[p.id] destroy();

    self.zmwp_hud[p.id] = undefined;
    self zmwp_hud_arrange();
}

zmwp_hud_arrange()
{
    layout = zmwp_hud_layout();
    n = 0;

    foreach ( id in level.zmwp_ids )
    {
        if ( !isdefined( self.zmwp_hud[id] ) )
            continue;

        self.zmwp_hud[id].x = layout[0] + n % layout[4] * layout[3];
        self.zmwp_hud[id].y = layout[1] - int( n / layout[4] ) * layout[3];
        n++;
    }
}

// ---------------------------------------------------------------- machines

// p.machines[mapname] = array of "x y z yaw" strings (from the perk's Lua `machines` table)
zmwp_spawn_machines()
{
    flag_wait( "initial_blackscreen_passed" );
    level.zmwp_machines_up = 1;

    foreach ( id in level.zmwp_ids )
        zmwp_spawn_perk_machines( level.zmwp[id] );
}

zmwp_spawn_perk_machines( p )
{
    map = getdvar( "mapname" );

    if ( isdefined( p.triggers ) || !isdefined( p.machines ) || !isdefined( p.machines[map] ) )
        return;

    p.triggers = [];

    foreach ( spot in p.machines[map] )
    {
        parts = strtok( spot, " " );

        if ( parts.size >= 3 )
        {
            yaw = 0;

            if ( parts.size >= 4 )
                yaw = float( parts[3] );

            zmwp_place( p, ( float( parts[0] ), float( parts[1] ), float( parts[2] ) ), ( 0, yaw, 0 ) );
        }
    }
}

zmwp_machine_model( p )
{
    if ( isdefined( p.machine ) && isdefined( level.zmwp_models[p.machine] ) )
        return p.machine;

    if ( isdefined( level.machine_assets ) && isdefined( level.machine_assets["juggernog"] ) )
        return level.machine_assets["juggernog"].on_model;

    return "zombie_vending_jugg_on";
}

zmwp_place( p, origin, angles )
{
    machine = spawn( "script_model", origin );
    machine.angles = angles;
    machine setmodel( zmwp_machine_model( p ) );
    trigger = spawn( "trigger_radius_use", origin + vectorscale( ( 0, 0, 1 ), 30 ), 0, 40, 70 );
    trigger setcursorhint( "HINT_NOICON" );
    trigger sethintstring( p.hint, p.cost );
    trigger usetriggerrequirelookat();
    trigger.script_noteworthy = "zmwp_" + p.id;
    trigger.power_on = 1;
    trigger.zmwp_machine = machine;
    trigger thread zmwp_machine_think( p );

    if ( !isdefined( p.triggers ) )
        p.triggers = [];

    p.triggers[p.triggers.size] = trigger;
    return machine;
}

zmwp_machine_think( p )
{
    level endon( "end_game" );
    self endon( "death" );

    while ( true )
    {
        self waittill( "trigger", player );

        if ( !is_player_valid( player ) || zmwp_owns( player, p ) || player.is_drinking > 0 )
            continue;

        if ( player.score < p.cost )
        {
            self playsound( "evt_perk_deny" );
            continue;
        }

        if ( player.num_perks >= player get_player_perk_purchase_limit() )
        {
            self playsound( "evt_perk_deny" );
            continue;
        }

        player maps\mp\zombies\_zm_score::minus_to_player_score( p.cost, 1 );
        self playsound( "zmb_cha_ching" );
        player thread zmwp_drink( p );
    }
}

// _zm_perks' vending_trigger_post_think / perk_give_bottle_begin / _end, for a perk _zm_perks doesn't know
zmwp_drink( p )
{
    self endon( "disconnect" );
    self endon( "end_game" );
    self endon( "perk_abort_drinking" );
    self increment_is_drinking();
    self disable_player_move_states( 1 );
    gun = self getcurrentweapon();
    bottle = zmwp_bottle( p );
    self giveweapon( bottle );
    self switchtoweapon( bottle );
    evt = self waittill_any_return( "fake_death", "death", "player_downed", "weapon_change_complete" );

    if ( evt == "weapon_change_complete" )
        self thread zmwp_wait_give( p );

    self enable_player_move_states();
    self takeweapon( bottle );

    if ( self maps\mp\zombies\_zm_laststand::player_is_in_laststand() || isdefined( self.intermission ) && self.intermission )
        return;

    if ( self is_multiple_drinking() )
    {
        self decrement_is_drinking();
        return;
    }

    if ( gun != "none" && !is_placeable_mine( gun ) && !is_equipment_that_blocks_purchase( gun ) )
    {
        self switchtoweapon( gun );

        if ( is_melee_weapon( gun ) )
        {
            self decrement_is_drinking();
            self notify( "burp" );
            return;
        }
    }
    else
    {
        primaries = self getweaponslistprimaries();

        if ( isdefined( primaries ) && primaries.size > 0 )
            self switchtoweapon( primaries[0] );
    }

    self waittill( "weapon_change_complete" );

    if ( !self maps\mp\zombies\_zm_laststand::player_is_in_laststand() && !( isdefined( self.intermission ) && self.intermission ) )
        self decrement_is_drinking();

    self notify( "burp" );
}

zmwp_wait_give( p )
{
    self endon( "player_downed" );
    self endon( "disconnect" );
    self endon( "end_game" );
    self endon( "perk_abort_drinking" );
    self waittill_notify_or_timeout( "burp", 0.5 );
    zmwp_give( self, p, 1 );
}

// ---------------------------------------------------------------- tool commands
// zmw_perk_cmd = "<serial> <action> [arg] [all]", one-shot (run once each time the serial changes). The player is
// the host, or every player when the last word is "all" (place and list: always the host).
//   give <id> | take <id>          a custom perk id, or a stock specialty such as specialty_armorvest
//   allperks | noperks             every perk the map sells plus every custom perk / all of them taken
//   points <n> | takepoints <n>    score
//   ammo | revive | heal           refill every weapon / get up from last stand / full health
//   place <id> | list
//   live <first> <count>           load perks from dvars zmw_ir_<first> .. zmw_ir_<first + count - 1> (see zmwi_load)
//   unload <id>                    take a perk from everyone and remove its machines
// place puts a machine in front of the host and prints "ZMW_PERK_PLACED <id> <map> <x> <y> <z> <yaw>" to the
// console log; the tool reads that line and saves the spot into the perk's Lua file (perk.machines).
// live answers with "ZMW_LIVE <serial> ok <id>" per perk, or "ZMW_LIVE <serial> fail <reason>".

zmwp_watch_commands()
{
    level endon( "end_game" );

    while ( true )
    {
        raw = getdvar( "zmw_perk_cmd" );

        if ( raw != level.zmwp_cmd_last )
        {
            level.zmwp_cmd_last = raw;
            args = strtok( raw, " " );
            players = getplayers();

            if ( args.size >= 4 && args[1] == "live" )
                zmwi_load( args[0], int( args[2] ), int( args[3] ) );
            else if ( args.size >= 3 && args[1] == "unload" )
                zmwp_unload( args[2] );
            else if ( args.size >= 2 && players.size > 0 )
            {
                id = "";

                if ( args.size >= 3 )
                    id = args[2];

                if ( args[args.size - 1] == "all" && args[1] != "place" && args[1] != "list" )
                {
                    foreach ( player in players )
                        zmwp_command( player, args[1], id );
                }
                else
                    zmwp_command( players[0], args[1], id );
            }
        }

        wait 0.25;
    }
}

zmwp_command( player, action, id )
{
    if ( action == "list" )
    {
        foreach ( pid in level.zmwp_ids )
        {
            live = "";

            if ( isdefined( level.zmwp[pid].live ) )
                live = ", live";

            iprintln( "ZM Workshop perk: " + pid + " (" + level.zmwp[pid].name + live + ")" );
        }

        return;
    }

    if ( action == "give" )
        zmwa_give_perk( player, id );
    else if ( action == "take" )
        zmwa_take_perk( player, id );
    else if ( action == "allperks" )
    {
        foreach ( perk in zmwp_all_perks() )
            zmwa_give_perk( player, perk );
    }
    else if ( action == "noperks" )
    {
        foreach ( perk in zmwp_all_perks() )
            zmwa_take_perk( player, perk );
    }
    else if ( action == "points" )
        zmwa_give_points( player, id );
    else if ( action == "takepoints" )
        zmwa_take_points( player, id );
    else if ( action == "ammo" )
    {
        foreach ( weapon in player getweaponslist() )
            player givemaxammo( weapon );
    }
    else if ( action == "revive" )
        zmwa_revive( player );
    else if ( action == "heal" )
        player.health = player.maxhealth;
    else if ( action == "place" && isdefined( level.zmwp[id] ) )
    {
        yaw = player.angles[1];
        origin = player.origin + vectorscale( anglestoforward( ( 0, yaw, 0 ) ), 64 );
        zmwp_place( level.zmwp[id], origin, ( 0, yaw + 180, 0 ) );
        println( "ZMW_PERK_PLACED " + id + " " + getdvar( "mapname" ) + " " + int( origin[0] ) + " " + int( origin[1] ) + " " +
                 int( origin[2] ) + " " + int( yaw + 180 ) );
        iprintln( "ZM Workshop: placed " + level.zmwp[id].name + " - the tool saves the spot" );
    }
}

zmwp_unload( id )
{
    if ( !isdefined( level.zmwp[id] ) )
        return;

    p = level.zmwp[id];

    foreach ( player in getplayers() )
        zmwp_take( player, p );

    wait 0.05;

    if ( isdefined( p.triggers ) )
    {
        foreach ( trigger in p.triggers )
        {
            if ( isdefined( trigger.zmwp_machine ) )
                trigger.zmwp_machine delete();

            trigger delete();
        }
    }

    ids = [];

    foreach ( pid in level.zmwp_ids )
    {
        if ( pid != id )
            ids[ids.size] = pid;
    }

    level.zmwp_ids = ids;
    level.zmwp[id] = undefined;
    iprintln( "ZM Workshop: removed " + p.name );
}

// The map's stock perks (its machines' specialties, without Pack-a-Punch) followed by every custom perk id.
zmwp_all_perks()
{
    perks = [];
    machines = getentarray( "zombie_vending", "targetname" );

    foreach ( machine in machines )
    {
        if ( isdefined( machine.script_noteworthy ) && machine.script_noteworthy != "specialty_weapupgrade" && !zmwp_in( perks, machine.script_noteworthy ) )
            perks[perks.size] = machine.script_noteworthy;
    }

    foreach ( id in level.zmwp_ids )
        perks[perks.size] = id;

    return perks;
}

zmwp_in( list, value )
{
    foreach ( v in list )
    {
        if ( v == value )
            return 1;
    }

    return 0;
}

// ---------------------------------------------------------------- live perks: lua2gsc's bytecode, interpreted
// The format is described in lua2gsc.h (detail::Live). A perk arrives as tokens split over console dvars; it is parsed
// once into structs (one per instruction) and run by zmwi_call, a flat loop over registers - flat because GSC limits
// how deeply calls nest. Lua tables are GSC arrays (lists, maps) or records (struct with .f, marked .zmwi_rec);
// entity fields a perk invents live in entity.zmwi_f. Only perks that changed are sent, and they are meant for trying
// changes: every instruction is a few script variables, and the engine has a fixed number of those.

zmwi_init()
{
    level.zmwi_ascii = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~";
    level.zmwi_hex = "0123456789ABCDEF";
}

zmwi_load( serial, first, count )
{
    toks = [];

    for ( i = 0; i < count; i++ )
    {
        foreach ( t in strtok( getdvar( "zmw_ir_" + ( first + i ) ), " " ) )
            toks[toks.size] = t;
    }

    st = spawnstruct();
    st.t = toks;
    st.at = 0;

    while ( st.at < st.t.size )
    {
        live = zmwi_parse( st );

        if ( !isdefined( live ) )
        {
            println( "ZMW_LIVE " + serial + " fail bad data at token " + st.at );
            iprintln( "ZM Workshop: a live perk didn't load (bad data) - it runs from the next map start" );
            return;
        }

        zmwi_install( live );
        println( "ZMW_LIVE " + serial + " ok " + live.id );
    }

    println( "ZMW_LIVE " + serial + " done" );
}

zmwi_next( st )
{
    t = st.t[st.at];
    st.at++;
    return t;
}

zmwi_int( st )
{
    return int( zmwi_next( st ) );
}

zmwi_parse( st )
{
    if ( zmwi_next( st ) != "ZMWI" )
        return undefined;

    zmwi_next( st );
    live = spawnstruct();
    live.id = zmwi_unesc( zmwi_next( st ) );
    live.fns = [];
    live.h = [];
    info = spawnstruct();
    info.id = live.id;
    live.info = info;

    while ( st.at < st.t.size )
    {
        w = zmwi_next( st );

        if ( w == "E" )
            return live;

        if ( w == "I" )
        {
            k = zmwi_next( st );
            v = zmwi_const( zmwi_next( st ) );

            switch ( k )
            {
                case "name":
                    info.name = v;
                    break;
                case "description":
                    info.description = v;
                    break;
                case "cost":
                    info.cost = v;
                    break;
                case "hint":
                    info.hint = v;
                    break;
                case "icon":
                    info.icon = v;
                    break;
                case "machine":
                    info.machine = v;
                    break;
                case "bottle":
                    info.bottle = v;
                    break;
                case "tick_every":
                    info.tick_every = v;
                    break;
            }
        }
        else if ( w == "C" )
        {
            r = zmwi_const( zmwi_next( st ) );
            g = zmwi_const( zmwi_next( st ) );
            b = zmwi_const( zmwi_next( st ) );
            info.color = ( r, g, b );
        }
        else if ( w == "M" )
        {
            map = zmwi_unesc( zmwi_next( st ) );
            n = zmwi_int( st );

            if ( !isdefined( info.machines ) )
                info.machines = [];

            spots = [];

            for ( i = 0; i < n; i++ )
                spots[i] = zmwi_const( zmwi_next( st ) );

            info.machines[map] = spots;
        }
        else if ( w == "S" )
        {
            n = zmwi_int( st );
            info.specialties = [];

            for ( i = 0; i < n; i++ )
                info.specialties[i] = zmwi_const( zmwi_next( st ) );
        }
        else if ( w == "F" )
        {
            fn = spawnstruct();
            fn.np = zmwi_int( st );
            zmwi_next( st );
            n = zmwi_int( st );
            code = [];

            for ( i = 0; i < n; i++ )
                code[i] = zmwi_ins( st );

            fn.code = code;
            live.fns[live.fns.size] = fn;
        }
        else if ( w == "H" )
        {
            h = zmwi_next( st );
            live.h[h] = zmwi_int( st );
        }
        else
            return undefined;
    }

    return undefined;
}

// one instruction: op plus a/b/c (registers, targets, function numbers), s (a name), k (a constant), n (argument registers)
zmwi_ins( st )
{
    ins = spawnstruct();
    op = zmwi_next( st );
    ins.op = op;

    switch ( op )
    {
        case "K":
            ins.a = zmwi_int( st );
            ins.k = zmwi_const( zmwi_next( st ) );
            break;
        case "MV":
        case "FN":
        case "NOT":
        case "NEG":
        case "LEN":
        case "JF":
        case "JT":
            ins.a = zmwi_int( st );
            ins.b = zmwi_int( st );
            break;
        case "GG":
            ins.a = zmwi_int( st );
            ins.s = zmwi_unesc( zmwi_next( st ) );
            break;
        case "GS":
            ins.s = zmwi_unesc( zmwi_next( st ) );
            ins.b = zmwi_int( st );
            break;
        case "PK":
        case "NL":
        case "NR":
        case "J":
        case "W":
        case "R":
            ins.a = zmwi_int( st );
            break;
        case "R0":
            break;
        case "GF":
            ins.a = zmwi_int( st );
            ins.b = zmwi_int( st );
            ins.s = zmwi_unesc( zmwi_next( st ) );
            break;
        case "SF":
            ins.a = zmwi_int( st );
            ins.s = zmwi_unesc( zmwi_next( st ) );
            ins.b = zmwi_int( st );
            break;
        case "CA":
            ins.a = zmwi_int( st );
            ins.s = zmwi_unesc( zmwi_next( st ) );
            ins.n = zmwi_regs( st );
            break;
        case "CM":
            ins.a = zmwi_int( st );
            ins.s = zmwi_unesc( zmwi_next( st ) );
            ins.b = zmwi_int( st );
            ins.n = zmwi_regs( st );
            break;
        case "CF":
        case "CV":
            ins.a = zmwi_int( st );
            ins.b = zmwi_int( st );
            ins.n = zmwi_regs( st );
            break;
        case "TH":
            ins.b = zmwi_int( st );
            ins.n = zmwi_regs( st );
            break;
        default:
            ins.a = zmwi_int( st );
            ins.b = zmwi_int( st );
            ins.c = zmwi_int( st );
            break;
    }

    return ins;
}

zmwi_regs( st )
{
    n = zmwi_int( st );
    regs = [];

    for ( i = 0; i < n; i++ )
        regs[i] = zmwi_int( st );

    return regs;
}

zmwi_const( t )
{
    kind = getsubstr( t, 0, 1 );
    rest = getsubstr( t, 1, t.size );

    if ( kind == "i" )
        return int( rest );

    if ( kind == "n" )
        return float( rest );

    if ( kind == "s" )
        return zmwi_unesc( rest );

    return undefined;
}

zmwi_unesc( s )
{
    if ( !issubstr( s, "%" ) )
        return s;

    out = "";

    for ( i = 0; i < s.size; i++ )
    {
        c = getsubstr( s, i, i + 1 );

        if ( c == "%" && i + 2 < s.size )
        {
            v = zmwi_hexval( getsubstr( s, i + 1, i + 2 ) ) * 16 + zmwi_hexval( getsubstr( s, i + 2, i + 3 ) );
            i = i + 2;

            if ( v >= 32 && v <= 126 )
                c = getsubstr( level.zmwi_ascii, v - 32, v - 31 );
            else if ( v == 10 )
                c = "\n";
            else
                c = " ";
        }

        out = out + c;
    }

    return out;
}

zmwi_hexval( c )
{
    for ( i = 0; i < 16; i++ )
    {
        if ( getsubstr( level.zmwi_hex, i, i + 1 ) == c )
            return i;
    }

    return 0;
}

// a perk loaded live replaces the compiled one (or an earlier live one) in place, so threads holding p see the
// new code; players who have it get on_take of the old version and on_give of the new one
zmwi_install( live )
{
    info = live.info;
    id = live.id;
    owners = [];

    if ( isdefined( level.zmwp[id] ) )
    {
        p = level.zmwp[id];

        foreach ( player in getplayers() )
        {
            if ( zmwp_owns( player, p ) )
            {
                owners[owners.size] = player;
                zmwp_fire( p, "take", player );
            }
        }
    }
    else
    {
        p = spawnstruct();
        p.id = id;
        level.zmwp[id] = p;
        level.zmwp_ids[level.zmwp_ids.size] = id;
    }

    p.name = info.name;
    p.description = info.description;
    p.cost = info.cost;
    p.hint = info.hint;
    p.icon = info.icon;
    p.color = info.color;
    p.machine = info.machine;
    p.bottle = info.bottle;
    p.machines = info.machines;
    p.specialties = info.specialties;
    p.tick_every = info.tick_every;
    zmwp_defaults( p );
    live.g = [];
    rec = spawnstruct();
    rec.zmwi_rec = 1;
    rec.f = [];
    rec.f["id"] = p.id;
    rec.f["name"] = p.name;
    rec.f["description"] = p.description;
    rec.f["cost"] = p.cost;
    rec.f["hint"] = p.hint;
    rec.f["icon"] = p.icon;
    live.rec = rec;
    p.live = live;
    zmwi_call( live, 0, [] );

    foreach ( player in owners )
    {
        player zmwp_hud_style( p );
        zmwp_fire( p, "give", player );
    }

    if ( isdefined( p.triggers ) )
    {
        foreach ( trigger in p.triggers )
            trigger sethintstring( p.hint, p.cost );
    }
    else if ( isdefined( level.zmwp_machines_up ) )
        zmwp_spawn_perk_machines( p );

    iprintln( "ZM Workshop: " + p.name + " loaded live" );
}

zmwi_truthy( x )
{
    if ( !isdefined( x ) )
        return 0;

    if ( isint( x ) || isfloat( x ) )
        return x != 0;

    return 1;
}

// is v something with fields? (structs, entities; GSC errors on .field of a number, string, array or vector)
zmwi_object( v )
{
    return isdefined( v ) && !isint( v ) && !isfloat( v ) && !isstring( v ) && !isarray( v ) && !isvec( v );
}

zmwi_get( o, key )
{
    if ( isarray( o ) )
        return o[key];

    if ( !zmwi_object( o ) )
        return undefined;

    if ( isdefined( o.zmwi_rec ) )
        return o.f[key];

    if ( isdefined( o.zmwi_fn ) )
        return undefined;

    switch ( key )
    {
        case "name":
            return o.name;
        case "score":
            return o.score;
        case "health":
            return o.health;
        case "maxhealth":
            return o.maxhealth;
        case "origin":
            return o.origin;
        case "angles":
            return o.angles;
        case "team":
            return o.team;
        case "animname":
            return o.animname;
        case "targetname":
            return o.targetname;
        case "script_noteworthy":
            return o.script_noteworthy;
        case "model":
            return o.model;
        case "classname":
            return o.classname;
        case "num_perks":
            return o.num_perks;
        case "is_drinking":
            return o.is_drinking;
        case "ignoreme":
            return o.ignoreme;
        case "damageweapon":
            return o.damageweapon;
        case "damagemod":
            return o.damagemod;
        case "attacker":
            return o.attacker;
        case "is_zombie":
            return o.is_zombie;
        case "sessionstate":
            return o.sessionstate;
    }

    if ( isdefined( o.zmwi_f ) )
        return o.zmwi_f[key];

    return undefined;
}

// o is a struct or entity (a reference), so setting through it sticks
zmwi_put( o, key, v )
{
    if ( !zmwi_object( o ) )
        return;

    if ( isdefined( o.zmwi_rec ) )
    {
        o.f[key] = v;
        return;
    }

    switch ( key )
    {
        case "health":
            o.health = v;
            return;
        case "ignoreme":
            o.ignoreme = v;
            return;
    }

    if ( !isdefined( o.zmwi_f ) )
        o.zmwi_f = [];

    o.zmwi_f[key] = v;
}

zmwi_args( r, regs )
{
    a = [];

    for ( i = 0; i < regs.size; i++ )
        a[i] = r[regs[i]];

    return a;
}

zmwi_call( live, fi, args )
{
    fn = live.fns[fi];
    r = [];

    for ( i = 0; i < fn.np; i++ )
        r[i] = args[i];

    code = fn.code;
    n = code.size;
    pc = 0;

    while ( pc < n )
    {
        ins = code[pc];
        pc++;

        switch ( ins.op )
        {
            case "K":
                r[ins.a] = ins.k;
                break;
            case "MV":
                r[ins.a] = r[ins.b];
                break;
            case "GG":
                r[ins.a] = live.g[ins.s];
                break;
            case "GS":
                live.g[ins.s] = r[ins.b];
                break;
            case "FN":
                f = spawnstruct();
                f.zmwi_fn = ins.b;
                f.zmwi_live = live;
                r[ins.a] = f;
                break;
            case "PK":
                r[ins.a] = live.rec;
                break;
            case "GF":
                r[ins.a] = zmwi_get( r[ins.b], ins.s );
                break;
            case "SF":
                if ( isarray( r[ins.a] ) )
                    r[ins.a][ins.s] = r[ins.b];
                else
                    zmwi_put( r[ins.a], ins.s, r[ins.b] );

                break;
            case "GI":
                r[ins.a] = zmwi_get( r[ins.b], zmw_idx( r[ins.c] ) );
                break;
            case "SI":
                key = zmw_idx( r[ins.b] );

                if ( isarray( r[ins.a] ) )
                    r[ins.a][key] = r[ins.c];
                else
                    zmwi_put( r[ins.a], key, r[ins.c] );

                break;
            case "NL":
                r[ins.a] = [];
                break;
            case "NR":
                t = spawnstruct();
                t.zmwi_rec = 1;
                t.f = [];
                r[ins.a] = t;
                break;
            case "ADD":
                r[ins.a] = r[ins.b] + r[ins.c];
                break;
            case "SUB":
                r[ins.a] = r[ins.b] - r[ins.c];
                break;
            case "MUL":
                r[ins.a] = r[ins.b] * r[ins.c];
                break;
            case "DIV":
                r[ins.a] = r[ins.b] * 1.0 / r[ins.c];
                break;
            case "IDIV":
                r[ins.a] = zmw_floordiv( r[ins.b], r[ins.c] );
                break;
            case "MOD":
                r[ins.a] = r[ins.b] % r[ins.c];
                break;
            case "POW":
                r[ins.a] = zmw_pow( r[ins.b], r[ins.c] );
                break;
            case "LT":
                r[ins.a] = r[ins.b] < r[ins.c];
                break;
            case "GT":
                r[ins.a] = r[ins.b] > r[ins.c];
                break;
            case "LE":
                r[ins.a] = r[ins.b] <= r[ins.c];
                break;
            case "GE":
                r[ins.a] = r[ins.b] >= r[ins.c];
                break;
            case "EQ":
                r[ins.a] = zmw_eq( r[ins.b], r[ins.c] );
                break;
            case "NE":
                r[ins.a] = !zmw_eq( r[ins.b], r[ins.c] );
                break;
            case "CAT":
                r[ins.a] = "" + zmwi_text( r[ins.b] ) + zmwi_text( r[ins.c] );
                break;
            case "NOT":
                r[ins.a] = !zmwi_truthy( r[ins.b] );
                break;
            case "NEG":
                r[ins.a] = 0 - r[ins.b];
                break;
            case "LEN":
                r[ins.a] = r[ins.b].size;
                break;
            case "J":
                pc = ins.a;
                break;
            case "JF":
                if ( !zmwi_truthy( r[ins.a] ) )
                    pc = ins.b;

                break;
            case "JT":
                if ( zmwi_truthy( r[ins.a] ) )
                    pc = ins.b;

                break;
            case "CA":
                r[ins.a] = zmwi_api( ins.s, zmwi_args( r, ins.n ) );
                break;
            case "CM":
                r[ins.a] = zmwi_method( ins.s, r[ins.b], zmwi_args( r, ins.n ) );
                break;
            case "CF":
                r[ins.a] = zmwi_call( live, ins.b, zmwi_args( r, ins.n ) );
                break;
            case "CV":
                fv = r[ins.b];

                if ( zmwi_object( fv ) && isdefined( fv.zmwi_fn ) )
                    r[ins.a] = zmwi_call( fv.zmwi_live, fv.zmwi_fn, zmwi_args( r, ins.n ) );

                break;
            case "TH":
                level thread zmwi_call( live, ins.b, zmwi_args( r, ins.n ) );
                break;
            case "W":
                wait( r[ins.a] );
                break;
            case "R":
                return r[ins.a];
            case "R0":
                return undefined;
        }
    }

    return undefined;
}

zmwi_text( x )
{
    if ( !isdefined( x ) )
        return "";

    return x;
}

// the perk API by its Lua name (lua2gsc's Globals / Library tables), for live perks
zmwi_api( name, a )
{
    switch ( name )
    {
        case "print":
            zmw_print( a[0] );
            return undefined;
        case "random":
        case "math.random":
            return zmw_random( a[0], a[1] );
        case "random_float":
            return zmw_random_float( a[0], a[1] );
        case "round_number":
            return zmw_round_number();
        case "time":
            return zmw_time();
        case "players":
            return zmw_players();
        case "zombies":
            return zmw_zombies();
        case "zombies_near":
            return zmw_zombies_near( a[0], a[1] );
        case "explode":
            zmw_explode( a[0], a[1], a[2], a[3], a[4] );
            return undefined;
        case "play_sound":
            zmw_play_sound( a[0], a[1] );
            return undefined;
        case "vector":
            return zmw_vector( a[0], a[1], a[2] );
        case "tostring":
            return zmw_tostring( a[0] );
        case "tonumber":
            return zmw_tonumber( a[0] );
        case "distance":
            return distance( a[0], a[1] );
        case "abs":
        case "math.abs":
            return abs( a[0] );
        case "floor":
        case "math.floor":
            return floor( a[0] );
        case "ceil":
        case "math.ceil":
            return ceil( a[0] );
        case "sqrt":
        case "math.sqrt":
            return sqrt( a[0] );
        case "min":
        case "math.min":
            return zmw_min( a[0], a[1] );
        case "max":
        case "math.max":
            return zmw_max( a[0], a[1] );
        case "string.lower":
            return zmw_lower( a[0] );
        case "string.sub":
            return zmw_sub( a[0], a[1], a[2] );
        case "string.find":
            return zmw_find( a[0], a[1] );
        case "table.contains":
            return zmw_contains( a[0], a[1] );
        case "__remove":
            return zmw_remove( a[0], a[1] );
        case "__keys":
            return getarraykeys( a[0] );
        case "__keyout":
            return zmw_key_out( a[0] );
    }

    iprintln( "ZM Workshop live perk: unknown function " + name );
    return undefined;
}

zmwi_method( name, e, a )
{
    if ( !isdefined( e ) )
        return undefined;

    switch ( name )
    {
        case "name":
            return zmwa_name( e );
        case "points":
            return zmwa_points( e );
        case "give_points":
            zmwa_give_points( e, a[0] );
            return undefined;
        case "take_points":
            zmwa_take_points( e, a[0] );
            return undefined;
        case "health":
            return zmwa_health( e );
        case "set_health":
            zmwa_set_health( e, a[0] );
            return undefined;
        case "max_health":
            return zmwa_max_health( e );
        case "set_max_health":
            zmwa_set_max_health( e, a[0] );
            return undefined;
        case "heal":
            zmwa_heal( e );
            return undefined;
        case "origin":
            return zmwa_origin( e );
        case "forward":
            return zmwa_forward( e );
        case "distance_to":
            return zmwa_distance_to( e, a[0] );
        case "is_alive":
            return zmwa_is_alive( e );
        case "is_downed":
            return zmwa_is_downed( e );
        case "revive":
            zmwa_revive( e );
            return undefined;
        case "current_weapon":
            return zmwa_current_weapon( e );
        case "give_weapon":
            zmwa_give_weapon( e, a[0] );
            return undefined;
        case "take_weapon":
            zmwa_take_weapon( e, a[0] );
            return undefined;
        case "refill_ammo":
            zmwa_refill_ammo( e );
            return undefined;
        case "set_speed":
            zmwa_set_speed( e, a[0] );
            return undefined;
        case "print":
            zmwa_print( e, a[0] );
            return undefined;
        case "print_bold":
            zmwa_print_bold( e, a[0] );
            return undefined;
        case "play_sound":
            zmwa_play_sound( e, a[0] );
            return undefined;
        case "is_sprinting":
            return zmwa_is_sprinting( e );
        case "is_on_ground":
            return zmwa_is_on_ground( e );
        case "stance":
            return zmwa_stance( e );
        case "set_ignored":
            zmwa_set_ignored( e, a[0] );
            return undefined;
        case "damage":
            zmwa_damage( e, a[0], a[1] );
            return undefined;
        case "kill":
            zmwa_kill( e, a[0] );
            return undefined;
        case "has_perk":
            return zmwa_has_perk( e, a[0] );
        case "give_perk":
            zmwa_give_perk( e, a[0] );
            return undefined;
        case "take_perk":
            zmwa_take_perk( e, a[0] );
            return undefined;
        case "shellshock":
            zmwa_shellshock( e, a[0], a[1] );
            return undefined;
        case "set_engine_perk":
            zmwa_set_engine_perk( e, a[0], a[1] );
            return undefined;
    }

    iprintln( "ZM Workshop live perk: unknown method " + name );
    return undefined;
}

// ---------------------------------------------------------------- API used by compiled Lua (see API.md)
// Lua arrays are 1-based; GSC arrays here stay 0-based and compiled code shifts number indices (zmw_idx).

zmw_idx( k )
{
    if ( isint( k ) )
        return k - 1;

    return k;
}

zmw_truthy( x )
{
    if ( !isdefined( x ) )
        return 0;

    if ( isstring( x ) || isarray( x ) || isplayer( x ) || isai( x ) )
        return 1;

    return x != 0;
}

zmw_eq( a, b )
{
    if ( !isdefined( a ) || !isdefined( b ) )
        return !isdefined( a ) && !isdefined( b );

    if ( isstring( a ) != isstring( b ) )
        return 0;

    return a == b;
}

zmw_or( a, b )
{
    if ( zmw_truthy( a ) )
        return a;

    return b;
}

zmw_and( a, b )
{
    if ( zmw_truthy( a ) )
        return b;

    return a;
}

zmw_pow( a, b )
{
    r = 1;

    for ( i = 0; i < b; i++ )
        r = r * a;

    return r;
}

zmw_floordiv( a, b )
{
    q = a / b;
    f = int( q );

    if ( f > q )
        f = f - 1;

    return f;
}

zmw_insert( t, v )
{
    t[t.size] = v;
    return t;
}

zmw_remove( t, i )
{
    out = [];

    for ( j = 0; j < t.size; j++ )
    {
        if ( j != i - 1 )
            out[out.size] = t[j];
    }

    return out;
}

zmw_contains( t, v )
{
    foreach ( x in t )
    {
        if ( x == v )
            return 1;
    }

    return 0;
}

zmw_keys( t )
{
    return getarraykeys( t );
}

zmw_key_out( k )
{
    if ( isint( k ) )
        return k + 1;

    return k;
}

zmw_print( msg )
{
    iprintln( msg );
}

zmw_random( a, b )
{
    if ( !isdefined( b ) )
        return randomint( a ) + 1;

    return randomintrange( a, b + 1 );
}

zmw_random_float( a, b )
{
    return randomfloatrange( a, b );
}

zmw_round_number()
{
    return level.round_number;
}

zmw_time()
{
    return gettime() / 1000;
}

zmw_players()
{
    return getplayers();
}

zmw_zombies()
{
    return get_round_enemy_array();
}

zmw_zombies_near( origin, radius )
{
    out = [];

    foreach ( zombie in get_round_enemy_array() )
    {
        if ( isalive( zombie ) && distancesquared( zombie.origin, origin ) <= radius * radius )
            out[out.size] = zombie;
    }

    return out;
}

zmw_explode( origin, radius, max_damage, min_damage, player )
{
    if ( !isdefined( min_damage ) )
        min_damage = 0;

    // the player's own perks decide whether they are hurt (radiusdamage would hit them too)
    foreach ( zombie in zmw_zombies_near( origin, radius ) )
    {
        scale = 1 - distance( zombie.origin, origin ) / radius;
        damage = int( min_damage + ( max_damage - min_damage ) * scale );

        if ( isdefined( player ) )
            zombie dodamage( damage, origin, player, player, "none", "MOD_GRENADE_SPLASH" );
        else
            zombie dodamage( damage, origin );
    }

    earthquake( 0.3, 0.5, origin, radius * 2 );
}

zmw_play_sound( alias, origin )
{
    playsoundatposition( alias, origin );
}

zmw_vector( x, y, z )
{
    return ( x, y, z );
}

zmw_tostring( x )
{
    if ( !isdefined( x ) )
        return "nil";

    return "" + x;
}

zmw_tonumber( s )
{
    return float( s );
}

zmw_lower( s )
{
    return tolower( s );
}

zmw_sub( s, i, j )
{
    if ( !isdefined( j ) )
        j = s.size;

    return getsubstr( s, i - 1, j );
}

zmw_find( s, part )
{
    return issubstr( s, part );
}

zmw_min( a, b )
{
    if ( a < b )
        return a;

    return b;
}

zmw_max( a, b )
{
    if ( a > b )
        return a;

    return b;
}

// ---- methods: player:name() compiles to zmwa_name( player )

zmwa_name( e )
{
    return e.name;
}

zmwa_points( e )
{
    return e.score;
}

zmwa_give_points( e, n )
{
    e maps\mp\zombies\_zm_score::add_to_player_score( int( n ) );
}

zmwa_take_points( e, n )
{
    e maps\mp\zombies\_zm_score::minus_to_player_score( int( n ), 1 );
}

zmwa_health( e )
{
    return e.health;
}

zmwa_set_health( e, n )
{
    e.health = int( n );
}

zmwa_max_health( e )
{
    return e.maxhealth;
}

zmwa_set_max_health( e, n )
{
    e setmaxhealth( int( n ) );
}

zmwa_heal( e )
{
    e.health = e.maxhealth;
}

zmwa_origin( e )
{
    return e.origin;
}

zmwa_forward( e )
{
    return anglestoforward( e.angles );
}

zmwa_distance_to( e, other )
{
    if ( isplayer( other ) || isai( other ) )
        return distance( e.origin, other.origin );

    return distance( e.origin, other );
}

zmwa_is_alive( e )
{
    return isalive( e );
}

zmwa_is_downed( e )
{
    return e maps\mp\zombies\_zm_laststand::player_is_in_laststand();
}

zmwa_revive( e )
{
    if ( e maps\mp\zombies\_zm_laststand::player_is_in_laststand() )
        e maps\mp\zombies\_zm_laststand::auto_revive( e );
}

zmwa_current_weapon( e )
{
    return e getcurrentweapon();
}

zmwa_give_weapon( e, weapon )
{
    e maps\mp\zombies\_zm_weapons::weapon_give( weapon );
}

zmwa_take_weapon( e, weapon )
{
    e takeweapon( weapon );
}

zmwa_refill_ammo( e )
{
    weapon = e getcurrentweapon();

    if ( weapon != "none" )
        e givemaxammo( weapon );
}

zmwa_set_speed( e, scale )
{
    e setmovespeedscale( scale );
}

zmwa_print( e, msg )
{
    e iprintln( msg );
}

zmwa_print_bold( e, msg )
{
    e iprintlnbold( msg );
}

zmwa_play_sound( e, alias )
{
    e playsoundtoplayer( alias, e );
}

zmwa_is_sprinting( e )
{
    return e issprinting();
}

zmwa_is_on_ground( e )
{
    return e isonground();
}

zmwa_stance( e )
{
    return e getstance();
}

zmwa_set_ignored( e, on )
{
    e.ignoreme = zmw_truthy( on );
}

zmwa_damage( e, n, attacker )
{
    if ( isdefined( attacker ) )
        e dodamage( int( n ), e.origin, attacker, attacker, "none", "MOD_UNKNOWN" );
    else
        e dodamage( int( n ), e.origin );
}

zmwa_kill( e, attacker )
{
    if ( isdefined( attacker ) )
        e dodamage( e.health + 666, e.origin, attacker, attacker, "none", "MOD_UNKNOWN" );
    else
        e dodamage( e.health + 666, e.origin );
}

// id: a custom perk id, or a stock specialty (which goes through _zm_perks as before)
zmwa_has_perk( e, id )
{
    if ( isdefined( level.zmwp[id] ) )
        return zmwp_owns( e, level.zmwp[id] );

    return e hasperk( id );
}

zmwa_give_perk( e, id )
{
    if ( isdefined( level.zmwp[id] ) )
    {
        zmwp_give( e, level.zmwp[id], 0 );
        return;
    }

    if ( !e hasperk( id ) )
        e maps\mp\zombies\_zm_perks::give_perk( id, 0 );
}

zmwa_take_perk( e, id )
{
    if ( isdefined( level.zmwp[id] ) )
        zmwp_take( e, level.zmwp[id] );
    else if ( e hasperk( id ) )
        e notify( id + "_stop" );
}

zmwa_shellshock( e, kind, seconds )
{
    e shellshock( kind, seconds );
}

// a raw engine perk on or off, without the stock perk's HUD, drinking or rules
zmwa_set_engine_perk( e, specialty, on )
{
    if ( zmw_truthy( on ) )
        e setperk( specialty );
    else
        e unsetperk( specialty );
}
