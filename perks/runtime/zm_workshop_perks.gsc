// ZM Workshop custom perks - runtime (Plutonium T6 Zombies).
//
// Perks are written in Lua against the API in perks/API.md; lua2gsc compiles each one to GSC and appends it to
// this file, followed by zmwp_register_all(), which calls every perk's register function. Each perk then:
//   - is a real BO2 perk: it borrows an engine specialty BO2 Zombies never uses (see zmwp_specialties) and is
//     registered through _zm_perks' level._custom_perks, so give_perk / perk limits / losing perks on down work;
//   - gets a HUD icon drawn here (stock icons come from client scripts we can't extend);
//   - can be bought from machines placed per map (zmwp_place) or given by the tool (dvar zmw_perk_cmd).
// Events reach the perk's Lua handlers through zmwp_fire / the damage hooks below.
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
    level.zmwp_spare = zmwp_specialties();
    zmwp_register_all();
    // the tool's commands (Player tab: points, stock perks, ammo...) work without any custom perk
    level.zmwp_cmd_last = getdvar( "zmw_perk_cmd" );
    level thread zmwp_watch_commands();

    if ( level.zmwp_ids.size == 0 )
        return;

    maps\mp\zombies\_zm::register_player_damage_callback( ::zmwp_player_damage );
    maps\mp\zombies\_zm_spawner::register_zombie_death_event_callback( ::zmwp_zombie_death );
    level thread zmwp_hook_actor_damage();
    level thread zmwp_connect();
    level thread zmwp_rounds();
    level thread zmwp_spawn_machines();
}

// Engine perks no Zombies script sets, takes or reads (checked against every patch_zm / zm_*_patch script);
// each custom perk takes the next one. Left out because Zombies uses them: gpsjammer (female animations),
// immunemms (Cymbal Monkey), noname (friendly fire), nomotionsensor (Vulture Aid), detectexplosive /
// showenemyequipment / disarmexplosive (equipment), earnmoremomentum (score), and the three that spawn
// protection sets then takes (nottargetedbyairsupport, nokillstreakreticle, nottargettedbysentry).
zmwp_specialties()
{
    return strtok( "specialty_immunecounteruav specialty_immuneemp specialty_immunenvthermal " +
                   "specialty_immunerangefinder specialty_reconnaissance specialty_killstreak specialty_loudenemies", " " );
}

// Called by each compiled perk's register function.
//   info: struct with id, name, cost, hint, icon, color, machine, bottle (any may be undefined but id)
//   h:    struct of handler function pointers (give, take, kill, hit, damaged, downed, revived, round, tick, tick_every)
zmwp_add( info, h )
{
    if ( level.zmwp_ids.size >= level.zmwp_spare.size )
    {
        iprintln( "ZM Workshop: too many custom perks, " + info.id + " skipped" );
        return;
    }

    info.specialty = level.zmwp_spare[level.zmwp_ids.size];
    info.handlers = h;

    if ( !isdefined( info.name ) )
        info.name = info.id;

    if ( !isdefined( info.cost ) )
        info.cost = 2500;

    if ( !isdefined( info.hint ) )
        info.hint = "Hold ^3[{+activate}]^7 for " + info.name + " [Cost: &&1]";

    if ( !isdefined( info.icon ) )
        info.icon = "specialty_juggernaut_zombies";

    level.zmwp[info.id] = info;
    level.zmwp_ids[level.zmwp_ids.size] = info.id;
    precacheshader( info.icon );
    maps\mp\zombies\_zm_perks::register_perk_basic_info( info.specialty, info.id, info.cost, info.hint, zmwp_bottle( info ) );
    maps\mp\zombies\_zm_perks::register_perk_threads( info.specialty, ::zmwp_give_thread, ::zmwp_take_thread );
}

zmwp_bottle( info )
{
    if ( isdefined( info.bottle ) )
        return info.bottle;

    return "zombie_perk_bottle_jugg";
}

// custom perk id (or stock specialty name) -> engine specialty
zmwp_specialty( id )
{
    if ( isdefined( level.zmwp[id] ) )
        return level.zmwp[id].specialty;

    return id;
}

zmwp_from_specialty( specialty )
{
    foreach ( id in level.zmwp_ids )
    {
        if ( level.zmwp[id].specialty == specialty )
            return level.zmwp[id];
    }

    return undefined;
}

// _zm_perks runs these with self = the player when the perk is given / lost; they don't say which perk, so the
// player's perks are compared with what the HUD shows.
zmwp_give_thread()
{
    foreach ( id in level.zmwp_ids )
    {
        p = level.zmwp[id];

        if ( self hasperk( p.specialty ) && !isdefined( self.zmwp_hud[id] ) )
        {
            self zmwp_hud_add( p );
            self thread zmwp_tick( p );
            zmwp_call( p.handlers.give, self );
        }
    }
}

zmwp_take_thread()
{
    foreach ( id in level.zmwp_ids )
    {
        p = level.zmwp[id];

        if ( !self hasperk( p.specialty ) && isdefined( self.zmwp_hud[id] ) )
        {
            self zmwp_hud_remove( p );
            self notify( "zmwp_lost_" + id );
            zmwp_call( p.handlers.take, self );
        }
    }
}

zmwp_call( f, a )
{
    if ( isdefined( f ) )
        return [[ f ]]( a );

    return undefined;
}

zmwp_call2( f, a, b )
{
    if ( isdefined( f ) )
        return [[ f ]]( a, b );

    return undefined;
}

// handler f( player ) every p.handlers.tick_every seconds while the player has the perk
zmwp_tick( p )
{
    if ( !isdefined( p.handlers.tick ) )
        return;

    self endon( "disconnect" );
    self endon( "zmwp_lost_" + p.id );
    every = 0.5;

    if ( isdefined( p.handlers.tick_every ) )
        every = p.handlers.tick_every;

    while ( true )
    {
        wait( every );
        [[ p.handlers.tick ]]( self );
    }
}

zmwp_has( player, p )
{
    return isdefined( player ) && isplayer( player ) && player hasperk( p.specialty );
}

// ---------------------------------------------------------------- events

zmwp_player_damage( einflictor, eattacker, idamage, idflags, smeansofdeath, sweapon, vpoint, vdir, shitloc, psoffsettime )
{
    damage = idamage;
    changed = 0;

    foreach ( id in level.zmwp_ids )
    {
        p = level.zmwp[id];

        if ( isdefined( p.handlers.damaged ) && zmwp_has( self, p ) )
        {
            result = [[ p.handlers.damaged ]]( self, eattacker, damage, smeansofdeath, sweapon );

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
    if ( isdefined( attacker ) && isplayer( attacker ) && isdefined( damage ) )
    {
        foreach ( id in level.zmwp_ids )
        {
            p = level.zmwp[id];

            if ( isdefined( p.handlers.hit ) && zmwp_has( attacker, p ) )
            {
                result = [[ p.handlers.hit ]]( attacker, self, damage, meansofdeath, weapon );

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

    if ( !isdefined( player ) || !isplayer( player ) )
        return;

    foreach ( id in level.zmwp_ids )
    {
        p = level.zmwp[id];

        if ( isdefined( p.handlers.kill ) && zmwp_has( player, p ) )
            player thread zmwp_kill_event( p, self, self.damageweapon, self.damagemod );
    }
}

zmwp_kill_event( p, zombie, weapon, means )
{
    [[ p.handlers.kill ]]( self, zombie, weapon, means );
}

zmwp_connect()
{
    while ( true )
    {
        level waittill( "connected", player );
        player thread zmwp_player_events();
    }
}

zmwp_player_events()
{
    self endon( "disconnect" );
    self.zmwp_hud = [];

    while ( true )
    {
        event = self waittill_any_return( "player_downed", "player_revived" );

        foreach ( id in level.zmwp_ids )
        {
            p = level.zmwp[id];

            if ( event == "player_downed" && isdefined( p.handlers.downed ) && self hasperk( p.specialty ) )
                self thread zmwp_call( p.handlers.downed, self );
            else if ( event == "player_revived" && isdefined( p.handlers.revived ) && self hasperk( p.specialty ) )
                self thread zmwp_call( p.handlers.revived, self );
        }
    }
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

            if ( !isdefined( p.handlers.round ) )
                continue;

            foreach ( player in getplayers() )
            {
                if ( player hasperk( p.specialty ) )
                    player thread zmwp_call2( p.handlers.round, player, level.round_number );
            }
        }
    }
}

// ---------------------------------------------------------------- HUD: custom icons in a row above the stock ones
// dvar zmw_perk_hud = "x y size gap" moves them (defaults below) without rebuilding.

zmwp_hud_layout()
{
    layout = [];
    layout[0] = 5;
    layout[1] = -110;
    layout[2] = 24;
    layout[3] = 28;
    raw = getdvar( "zmw_perk_hud" );

    if ( raw != "" )
    {
        parts = strtok( raw, " " );

        for ( i = 0; i < parts.size && i < 4; i++ )
            layout[i] = int( parts[i] );
    }

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

    if ( isdefined( p.color ) )
        hud.color = p.color;

    layout = zmwp_hud_layout();
    hud setshader( p.icon, layout[2], layout[2] );
    self.zmwp_hud[p.id] = hud;
    self zmwp_hud_arrange();
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

        self.zmwp_hud[id].x = layout[0] + n * layout[3];
        self.zmwp_hud[id].y = layout[1];
        n++;
    }
}

// ---------------------------------------------------------------- machines

// p.machines[mapname] = array of "x y z yaw" strings (from the perk's Lua `machines` table)
zmwp_spawn_machines()
{
    flag_wait( "initial_blackscreen_passed" );
    map = getdvar( "mapname" );

    foreach ( id in level.zmwp_ids )
    {
        p = level.zmwp[id];

        if ( !isdefined( p.machines ) || !isdefined( p.machines[map] ) )
            continue;

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
}

zmwp_machine_model( p )
{
    if ( isdefined( p.machine ) )
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
    trigger.script_noteworthy = p.specialty;
    trigger.power_on = 1;
    trigger thread zmwp_machine_think( p );
    return machine;
}

zmwp_machine_think( p )
{
    level endon( "end_game" );

    while ( true )
    {
        self waittill( "trigger", player );

        if ( !is_player_valid( player ) || player hasperk( p.specialty ) || player.is_drinking > 0 )
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
        level._custom_perks[p.specialty].perk_bottle = zmwp_bottle( p );
        self thread maps\mp\zombies\_zm_perks::vending_trigger_post_think( player, p.specialty );
    }
}

// ---------------------------------------------------------------- tool commands
// zmw_perk_cmd = "<serial> <action> [arg] [all]", one-shot (run once each time the serial changes). The player is
// the host, or every player when the last word is "all" (place and list: always the host).
//   give <id> | take <id>          a custom perk id, or a stock specialty such as specialty_armorvest
//   allperks | noperks             every perk the map sells plus every custom perk / all of them taken
//   points <n> | takepoints <n>    score
//   ammo | revive | heal           refill every weapon / get up from last stand / full health
//   place <id> | list
// place puts a machine in front of the host and prints "ZMW_PERK_PLACED <id> <map> <x> <y> <z> <yaw>" to the
// console log; the tool reads that line and saves the spot into the perk's Lua file (perk.machines).

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

            if ( args.size >= 2 && players.size > 0 )
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
            iprintln( "ZM Workshop perk: " + pid + " (" + level.zmwp[pid].name + ")" );

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
    {
        if ( !zmwp_in( perks, level.zmwp[id].specialty ) )
            perks[perks.size] = id;
    }

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

zmwa_has_perk( e, id )
{
    return e hasperk( zmwp_specialty( id ) );
}

zmwa_give_perk( e, id )
{
    specialty = zmwp_specialty( id );

    if ( e hasperk( specialty ) )
        return;

    e maps\mp\zombies\_zm_perks::give_perk( specialty, 0 );
}

zmwa_take_perk( e, id )
{
    specialty = zmwp_specialty( id );

    if ( e hasperk( specialty ) )
        e notify( specialty + "_stop" );
}

zmwa_shellshock( e, kind, seconds )
{
    e shellshock( kind, seconds );
}

