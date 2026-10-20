#include "SoundAliasJsonDumperT4.h"
#include <format>
#include <iomanip>
#include <nlohmann/json.hpp>
#include <algorithm>

using namespace T4;
using nlohmann::json;
namespace
{
    std::string Name(const char* text)
    {
        return text ? (text[0] == ',' ? text + 1 : text) : "";
    }
}
void sound::DriverGlobalsJsonDumperT4::DumpAsset(AssetDumpingContext& context, const XAssetInfo<SndDriverGlobals>& asset)
{
    const auto& globals = *asset.Asset();
    json out = {{"_type", "waw2bo2_sound_globals"}, {"_game", "T4"}, {"_version", 1}};
    const auto boundedName = [](const char (&name)[32]) { return std::string(name, std::find(name, name + 32, '\0')); };
    out["buses"] = json::array();
    for (unsigned i = 0; i < 64; ++i)
    {
        const auto& bus = globals.buses[i];
        out["buses"].push_back({{"index", i}, {"name", boundedName(bus.name)}, {"volumeMod", bus.volumeMod},
            {"maxVoices", bus.maxVoices}, {"restricted", bus.restricted}, {"pausable", bus.pausable},
            {"stopOnDeath", bus.stopOnDeath}, {"isMusic", bus.isMusic}, {"category", bus.category},
            {"voiceLimitType", bus.voiceLimitType}});
    }
    out["curves"] = json::array();
    out["speakerMaps"] = json::array();
    for (unsigned i = 0; i < 32; ++i)
    {
        const auto& curve = globals.curves[i];
        out["curves"].push_back({{"index", i}, {"name", boundedName(curve.name)}, {"pointCount", curve.pointCount},
                                 {"points", curve.points}});
        const auto& speakers = globals.speakerMaps[i];
        json set = {{"index", i}, {"name", boundedName(speakers.name)}, {"maps", json::array()}};
        for (const auto& map : speakers.channelMaps)
            set["maps"].push_back({{"inputChannels", map.input_channel_count}, {"outputChannels", map.output_channel_count},
                                   {"volumes", map.volumes}});
        out["speakerMaps"].push_back(std::move(set));
    }
    out["reverbPatches"] = json::array();
    for (unsigned i = 0; i < 64; ++i)
    {
        const auto& patch = globals.reverbPatches[i];
        json row = {{"index", i}, {"name", boundedName(patch.name)}};
#define PATCH_FIELD(field) row[#field] = patch.field
        PATCH_FIELD(room); PATCH_FIELD(roomHF); PATCH_FIELD(roomRolloffFactor); PATCH_FIELD(decayTime);
        PATCH_FIELD(decayHFRatio); PATCH_FIELD(reflections); PATCH_FIELD(reflectionsDelay); PATCH_FIELD(reverb);
        PATCH_FIELD(reverbDelay); PATCH_FIELD(diffusion); PATCH_FIELD(density); PATCH_FIELD(HFReference);
#undef PATCH_FIELD
        out["reverbPatches"].push_back(std::move(row));
    }
    out["masterEffects"] = json::array();
    for (unsigned i = 0; i < 16; ++i)
    {
        const auto& master = globals.masterEffects[i];
        out["masterEffects"].push_back({{"index", i}, {"name", boundedName(master.name)},
            {"masterRingmod", master.masterRingmod}, {"reverbRingmod", master.reverbRingmod},
            {"masterLPRatio", master.masterLPRatio}, {"masterLPDB", master.masterLPDB},
            {"masterHPRatio", master.masterHPRatio}, {"masterHPDB", master.masterHPDB}});
    }
    const auto file = context.OpenAssetFile(std::format("soundglobals/{}.w2bsndglobals.json", asset.m_name));
    if (file) *file << std::setw(2) << out << '\n';
}
void sound::AliasJsonDumperT4::DumpAsset(AssetDumpingContext& context, const XAssetInfo<snd_alias_list_t>& asset)
{
    const auto* list = asset.Asset();
    // Layout verified against the official WaW linker sub_404D50. Previous
    // gap fields are team modulation, entity limits and cylindrical falloff;
    // moveTime is FLOAT, not unsigned milliseconds. Offsets/size are unchanged.
    static_assert(sizeof(snd_alias_t) == 184 && offsetof(snd_alias_t, flags) == 132);
    json out = {{"_type", "waw2bo2_sound"}, {"_game", "T4"}, {"_version", 2},
                {"name", Name(list->aliasName)}, {"aliases", json::array()}};
    for (int i = 0; i < list->count; ++i)
    {
        const auto& a = list->head[i];
        json row = {{"aliasName", Name(a.aliasName)}, {"aliasNameHash", a.aliasNameHash},
                    {"subtitle", Name(a.subtitle)}, {"secondaryAliasName", Name(a.secondaryAliasName)},
                    {"chainAliasName", Name(a.chainAliasName)}};
#define FIELD(field) row[#field] = a.field
        FIELD(sequence); FIELD(volMin); FIELD(volMax); FIELD(pitchMin); FIELD(pitchMax);
        FIELD(distMin); FIELD(distMax); FIELD(distReverbMax); FIELD(slavePercentage); FIELD(probability);
        FIELD(lfePercentage); FIELD(centerPercentage); FIELD(envelopMin); FIELD(envelopMax);
        FIELD(envelopPercentage); FIELD(minPriority); FIELD(maxPriority); FIELD(minPriorityThreshold);
        FIELD(maxPriorityThreshold); FIELD(reverbSend); FIELD(teamVolMod); FIELD(teamPitchMod);
        FIELD(occlusionLevel); FIELD(occlusionWetDry); FIELD(moveTime); FIELD(startDelay); FIELD(speakerMap);
        FIELD(flags); FIELD(volumeFalloffCurve); FIELD(reverbFalloffCurve); FIELD(volumeMinFalloffCurve);
        FIELD(reverbMinFalloffCurve); FIELD(limitCount); FIELD(limitType); FIELD(entityLimitCount);
        FIELD(entityLimitType); FIELD(randomizeType); FIELD(cylInnerRadius); FIELD(cylOuterRadius); FIELD(cylOuterLevel);
#undef FIELD
        if (a.soundFile)
        {
            const auto& f = *a.soundFile;
            json file = {{"type", f.type}, {"exists", f.exists}};
            if (f.type == SAT_LOADED && f.u.loadSnd)
                file["name"] = Name(f.u.loadSnd->name);
            else if (f.type == SAT_STREAMED || f.type == SAT_PRIMED)
            {
                file["dir"] = Name(f.u.streamSnd.filename.dir);
                file["name"] = Name(f.u.streamSnd.filename.name);
                file["hash"] = f.u.streamSnd.filename.hash;
                if (f.u.streamSnd.primeSnd) file["primedName"] = Name(f.u.streamSnd.primeSnd->name);
            }
            row["soundFile"] = file;
        }
        else row["soundFile"] = nullptr;
        out["aliases"].push_back(row);
    }
    const auto file = context.OpenAssetFile(std::format("soundaliases/{}.w2bsnd.json", asset.m_name));
    if (file) *file << std::setw(2) << out << '\n';
}
