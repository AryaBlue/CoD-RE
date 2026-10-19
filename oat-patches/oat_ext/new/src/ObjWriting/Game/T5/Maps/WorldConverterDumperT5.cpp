#include "WorldConverterDumperT5.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <format>
#include <iomanip>
#include <map>
#include <nlohmann/json.hpp>
#include <ostream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace T5;

// Same interchange formats and versions as WorldConverterDumperT4 (gfx v6, clip v9, paths v1): the converter's
// readers stay unchanged. Values BO1 lays out differently are mapped to the WaW fields here.
namespace
{
    constexpr std::array<char, 8> MAGIC{'W', '2', 'B', 'S', 'P', '0', '0', '1'};

    template<typename T> void Write(std::ostream& stream, const T& value)
    {
        stream.write(reinterpret_cast<const char*>(&value), sizeof(value));
        if (!stream)
            throw std::runtime_error("Could not write BO1 world interchange data");
    }

    template<typename T> void WriteArray(std::ostream& stream, const T* values, const size_t count)
    {
        if (count && !values)
            throw std::runtime_error("BO1 world asset contains a null array");
        stream.write(reinterpret_cast<const char*>(values), static_cast<std::streamsize>(sizeof(T) * count));
        if (!stream)
            throw std::runtime_error("Could not write BO1 world interchange array");
    }

    void WriteString(std::ostream& stream, const char* value)
    {
        // a leading comma is OAT's asset reference marker; the interchange uses canonical names
        const std::string text = value && value[0] == ',' ? std::string(value + 1) : (value ? value : "");
        Write(stream, static_cast<uint32_t>(text.size()));
        stream.write(text.data(), static_cast<std::streamsize>(text.size()));
    }

    // BO1 generated (layered) world materials are named "*<id>(<layers>)"; OAT dumps them to
    // materials/generated/_<id>.json, so the interchange names them the same way
    std::string MaterialName(const char* value)
    {
        std::string name = value && value[0] == ',' ? std::string(value + 1) : (value ? value : "");
        if (!name.empty() && name[0] == '*')
        {
            std::ranges::replace(name, '*', '_');
            if (const auto paren = name.find('('); paren != std::string::npos)
                name.erase(paren);
            name = "generated/" + name;
        }
        return name;
    }

    std::string OutputName(const std::string& assetName, const char* suffix)
    {
        return std::format("waw2bo2/{}{}", assetName, suffix);
    }

    void WritePlane(std::ostream& stream, const float x, const float y, const float z, const float distance, const uint32_t material)
    {
        Write(stream, x);
        Write(stream, y);
        Write(stream, z);
        Write(stream, distance);
        Write(stream, material);
    }

    // BO1 brush sides carry content/surface flags where WaW stores a clip material index. Sides map back to the
    // first clip material with the same flags; flag pairs without one get an appended material entry.
    class ClipMaterialTable
    {
    public:
        explicit ClipMaterialTable(const clipMap_t& clip)
        {
            for (uint32_t i = 0; i < clip.numMaterials; ++i)
            {
                const auto& mat = clip.materials[i];
                m_names.emplace_back(mat.material);
                m_flags.emplace_back(mat.surfaceFlags, mat.contentFlags);
                m_lookup.try_emplace({mat.contentFlags, mat.surfaceFlags}, i);
            }
        }

        uint32_t Index(const int contentFlags, const int surfaceFlags)
        {
            const auto [it, added] = m_lookup.try_emplace({contentFlags, surfaceFlags}, static_cast<uint32_t>(m_names.size()));
            if (added)
            {
                m_names.emplace_back(std::format("bo1_clip_c{:08x}_s{:08x}", static_cast<uint32_t>(contentFlags), static_cast<uint32_t>(surfaceFlags)));
                m_flags.emplace_back(surfaceFlags, contentFlags);
            }
            return it->second;
        }

        void Write(std::ostream& stream) const
        {
            ::Write(stream, static_cast<uint32_t>(m_names.size()));
            for (size_t i = 0; i < m_names.size(); ++i)
            {
                WriteString(stream, m_names[i].c_str());
                ::Write(stream, m_flags[i].first);
                ::Write(stream, m_flags[i].second);
            }
        }

    private:
        std::vector<std::string> m_names;
        std::vector<std::pair<int, int>> m_flags; // surfaceFlags, contentFlags
        std::map<std::pair<int, int>, uint32_t> m_lookup;
    };

    void DumpClipMap(AssetDumpingContext& context, const std::string& assetName, const clipMap_t* clip)
    {
        // authored physics joints and their rendered ropes
        const auto constraintFile = context.OpenAssetFile(OutputName(assetName, ".constraints.json"));
        if (constraintFile)
        {
            const auto& strings = context.m_zone.m_script_strings;
            const auto str = [&strings](unsigned id)
            {
                return id && id < strings.Count() ? strings.Value(id) : std::string();
            };
            const auto vec = [](const vec3_t& v)
            {
                return nlohmann::json::array({v.x, v.y, v.z});
            };
            nlohmann::json entries = nlohmann::json::array();
            for (int i = 0; i < clip->num_constraints; i++)
            {
                const auto& c = clip->constraints[i];
                entries.push_back({{"targetname", str(c.targetname)},
                                   {"type", static_cast<int>(c.type)},
                                   {"attach_point_type1", static_cast<int>(c.attach_point_type1)},
                                   {"target_index1", c.target_index1},
                                   {"target_ent1", str(c.target_ent1)},
                                   {"target_bone1", c.target_bone1 ? c.target_bone1 : ""},
                                   {"attach_point_type2", static_cast<int>(c.attach_point_type2)},
                                   {"target_index2", c.target_index2},
                                   {"target_ent2", str(c.target_ent2)},
                                   {"target_bone2", c.target_bone2 ? c.target_bone2 : ""},
                                   {"offset", vec(c.offset)},
                                   {"pos", vec(c.pos)},
                                   {"pos2", vec(c.pos2)},
                                   {"dir", vec(c.dir)},
                                   {"flags", c.flags},
                                   {"timeout", c.timeout},
                                   {"min_health", c.min_health},
                                   {"max_health", c.max_health},
                                   {"distance", c.distance},
                                   {"damp", c.damp},
                                   {"power", c.power},
                                   {"scale", vec(c.scale)},
                                   {"spin_scale", c.spin_scale},
                                   {"minAngle", c.minAngle},
                                   {"maxAngle", c.maxAngle},
                                   {"material", c.material && c.material->info.name ? c.material->info.name : ""},
                                   {"constraintHandle", c.constraintHandle},
                                   {"rope_index", c.rope_index}});
            }
            *constraintFile << nlohmann::json({{"version", 1}, {"constraints", entries}}).dump(2);
        }

        const auto file = context.OpenAssetFile(OutputName(assetName, ".clip.bin"));
        if (!file)
            return;

        // resolve brush side materials first: the material table precedes the brushes
        ClipMaterialTable materials(*clip);
        std::vector<std::vector<uint32_t>> brushPlaneMaterials(clip->numBrushes);
        for (uint32_t i = 0; i < clip->numBrushes; ++i)
        {
            const auto& brush = clip->brushes[i];
            auto& planes = brushPlaneMaterials[i];
            // axial planes in WaW order: -x, +x, -y, +y, -z, +z
            for (int axis = 0; axis < 3; ++axis)
                for (int side = 0; side < 2; ++side)
                    planes.push_back(materials.Index(brush.axial_cflags[side][axis], brush.axial_sflags[side][axis]));
            for (uint32_t s = 0; s < brush.numsides; ++s)
                planes.push_back(materials.Index(brush.sides[s].cflags, brush.sides[s].sflags));
        }

        auto& stream = *file;
        WriteArray(stream, MAGIC.data(), MAGIC.size());
        Write(stream, uint32_t{9});
        WriteString(stream, clip->name);
        materials.Write(stream);

        Write(stream, clip->vertCount);
        WriteArray(stream, clip->verts, clip->vertCount);
        Write(stream, static_cast<uint32_t>(clip->triCount));
        WriteArray(stream, clip->triIndices, static_cast<size_t>(clip->triCount) * 3);

        Write(stream, static_cast<uint32_t>(clip->numBrushes));
        for (uint32_t i = 0; i < clip->numBrushes; ++i)
        {
            const auto& brush = clip->brushes[i];
            const auto& planeMaterials = brushPlaneMaterials[i];
            WriteArray(stream, brush.mins, 3);
            WriteArray(stream, brush.maxs, 3);
            Write(stream, brush.contents);
            Write(stream, static_cast<uint32_t>(brush.numsides + 6));

            WritePlane(stream, -1.0f, 0.0f, 0.0f, -brush.mins[0], planeMaterials[0]);
            WritePlane(stream, 1.0f, 0.0f, 0.0f, brush.maxs[0], planeMaterials[1]);
            WritePlane(stream, 0.0f, -1.0f, 0.0f, -brush.mins[1], planeMaterials[2]);
            WritePlane(stream, 0.0f, 1.0f, 0.0f, brush.maxs[1], planeMaterials[3]);
            WritePlane(stream, 0.0f, 0.0f, -1.0f, -brush.mins[2], planeMaterials[4]);
            WritePlane(stream, 0.0f, 0.0f, 1.0f, brush.maxs[2], planeMaterials[5]);
            for (uint32_t side = 0; side < brush.numsides; ++side)
            {
                const auto& source = brush.sides[side];
                if (!source.plane)
                    throw std::runtime_error("BO1 brush contains a null side plane");
                WritePlane(stream, source.plane->normal.x, source.plane->normal.y, source.plane->normal.z, source.plane->dist, planeMaterials[6 + side]);
            }

            Write(stream, brush.numverts);
            WriteArray(stream, brush.verts, brush.numverts);
        }

        // brushes reachable from each submodel: cmodel 0 is the world, the others belong to entities
        Write(stream, clip->numSubModels);
        for (uint32_t i = 0; i < clip->numSubModels; ++i)
        {
            const auto& model = clip->cmodels[i];
            WriteArray(stream, model.mins, 3);
            WriteArray(stream, model.maxs, 3);

            std::vector<uint16_t> owned;
            std::set<uint32_t> visited;
            std::set<uint16_t> seenBrushes;
            std::vector<uint32_t> pending;
            if (i == 0)
            {
                for (uint32_t leaf = 0; leaf < clip->numLeafs; ++leaf)
                    if (clip->leafs[leaf].brushContents && clip->leafs[leaf].leafBrushNode >= 0)
                        pending.push_back(static_cast<uint32_t>(clip->leafs[leaf].leafBrushNode));
            }
            else if (model.leaf.brushContents && model.leaf.leafBrushNode >= 0)
                pending.push_back(static_cast<uint32_t>(model.leaf.leafBrushNode));
            while (!pending.empty())
            {
                const auto index = pending.back();
                pending.pop_back();
                if (index >= clip->leafbrushNodesCount || !visited.insert(index).second)
                    continue;
                const auto& node = clip->leafbrushNodes[index];
                if (node.leafBrushCount > 0)
                {
                    for (int16_t b = 0; b < node.leafBrushCount; ++b)
                        if (seenBrushes.insert(node.data.leaf.brushes[b]).second)
                            owned.push_back(node.data.leaf.brushes[b]);
                    continue;
                }
                if (node.leafBrushCount < 0)
                    pending.push_back(index + 1);
                for (const auto offset : node.data.children.childOffset)
                    if (offset)
                        pending.push_back(index + offset);
            }
            Write(stream, static_cast<uint32_t>(owned.size()));
            WriteArray(stream, owned.data(), owned.size());
        }

        // collidable static models with their model-space collision hulls
        Write(stream, clip->numStaticModels);
        for (uint32_t i = 0; i < clip->numStaticModels; ++i)
        {
            const auto& sm = clip->staticModelList[i];
            const auto* model = sm.xmodel;
            WriteString(stream, model ? model->name : "");
            WriteArray(stream, sm.origin, 3);
            WriteArray(stream, sm.invScaledAxis[0], 9);
            WriteArray(stream, sm.absmin, 3);
            WriteArray(stream, sm.absmax, 3);
            Write(stream, model ? model->contents : 0);
            const auto surfCount = model && model->collSurfs ? static_cast<uint32_t>(model->numCollSurfs) : 0u;
            Write(stream, surfCount);
            for (uint32_t s = 0; s < surfCount; ++s)
            {
                const auto& surf = model->collSurfs[s];
                Write(stream, surf.contents);
                Write(stream, surf.surfFlags);
                WriteArray(stream, surf.mins, 3);
                WriteArray(stream, surf.maxs, 3);
                Write(stream, surf.boneIdx);
                Write(stream, static_cast<uint32_t>(surf.numCollTris));
                for (int t = 0; t < surf.numCollTris; ++t)
                {
                    WriteArray(stream, surf.collTris[t].plane, 4);
                    WriteArray(stream, surf.collTris[t].svec, 4);
                    WriteArray(stream, surf.collTris[t].tvec, 4);
                }
            }
        }

        // clip material of every collision triangle (from the aabb leaf nodes)
        std::vector<uint16_t> triMaterial(static_cast<size_t>(clip->triCount), 0xFFFF);
        for (int a = 0; a < clip->aabbTreeCount; ++a)
        {
            const auto& tree = clip->aabbTrees[a];
            if (tree.childCount != 0 || tree.u.partitionIndex < 0 || tree.u.partitionIndex >= clip->partitionCount)
                continue;
            const auto& partition = clip->partitions[tree.u.partitionIndex];
            for (int t = 0; t < static_cast<unsigned char>(partition.triCount); ++t)
            {
                const auto tri = static_cast<size_t>(partition.firstTri + t);
                if (tri < triMaterial.size())
                    triMaterial[tri] = tree.materialIndex;
            }
        }
        Write(stream, static_cast<uint32_t>(triMaterial.size()));
        WriteArray(stream, triMaterial.data(), triMaterial.size());

        // walkable bit of every triangle edge
        const auto edgeBytes = static_cast<uint32_t>((3 * clip->triCount + 31) / 32 * 4);
        Write(stream, edgeBytes);
        if (edgeBytes && clip->triEdgeIsWalkable)
            WriteArray(stream, clip->triEdgeIsWalkable, edgeBytes);
        else
            for (uint32_t i = 0; i < edgeBytes; ++i)
                Write(stream, uint8_t{0xFF});

        // terrain aabb tree, leaf roots and partitions
        Write(stream, static_cast<uint32_t>(clip->aabbTreeCount));
        for (int a = 0; a < clip->aabbTreeCount; ++a)
        {
            const auto& tree = clip->aabbTrees[a];
            Write(stream, tree.materialIndex);
            Write(stream, tree.childCount);
            Write(stream, tree.u.firstChildIndex);
        }
        Write(stream, static_cast<uint32_t>(clip->numLeafs));
        for (uint32_t l = 0; l < clip->numLeafs; ++l)
        {
            Write(stream, static_cast<uint32_t>(clip->leafs[l].firstCollAabbIndex));
            Write(stream, static_cast<uint32_t>(clip->leafs[l].collAabbCount));
            Write(stream, clip->leafs[l].terrainContents);
        }
        Write(stream, static_cast<uint32_t>(clip->partitionCount));
        for (int p = 0; p < clip->partitionCount; ++p)
        {
            Write(stream, static_cast<uint32_t>(clip->partitions[p].firstTri));
            Write(stream, static_cast<uint32_t>(static_cast<uint8_t>(clip->partitions[p].triCount)));
        }

        // effective brush masks reached through all authored leaf trees
        std::vector<int> reach(clip->numBrushes, 0);
        const auto visitLeaf = [&](const cLeaf_s& leaf)
        {
            std::vector<std::pair<uint32_t, int>> pending;
            std::set<std::pair<uint32_t, int>> visited;
            if (leaf.brushContents && leaf.leafBrushNode >= 0)
                pending.emplace_back(leaf.leafBrushNode, leaf.brushContents);
            while (!pending.empty())
            {
                const auto [index, inherited] = pending.back();
                pending.pop_back();
                if (index >= clip->leafbrushNodesCount || !visited.emplace(index, inherited).second)
                    continue;
                const auto& node = clip->leafbrushNodes[index];
                const int mask = inherited & node.contents;
                if (node.leafBrushCount > 0)
                {
                    for (int b = 0; b < node.leafBrushCount; b++)
                    {
                        const auto brush = node.data.leaf.brushes[b];
                        if (brush < clip->numBrushes)
                            reach[brush] |= mask & clip->brushes[brush].contents;
                    }
                    continue;
                }
                if (node.leafBrushCount < 0)
                    pending.emplace_back(index + 1, mask);
                for (const auto offset : node.data.children.childOffset)
                    if (offset)
                        pending.emplace_back(index + offset, mask);
            }
        };
        for (uint32_t i = 0; i < clip->numLeafs; i++)
            visitLeaf(clip->leafs[i]);
        for (uint32_t i = 1; i < clip->numSubModels; i++)
            visitLeaf(clip->cmodels[i].leaf);
        Write(stream, static_cast<uint32_t>(clip->numBrushes));
        WriteArray(stream, reach.data(), reach.size());

        // terrain in a moving cmodel is not owned by the world's BSP leafs
        Write(stream, clip->numSubModels);
        for (uint32_t i = 0; i < clip->numSubModels; i++)
        {
            const auto& leaf = clip->cmodels[i].leaf;
            Write(stream, static_cast<uint32_t>(leaf.firstCollAabbIndex));
            Write(stream, static_cast<uint32_t>(leaf.collAabbCount));
            Write(stream, leaf.terrainContents);
        }
    }

    std::string JsonString(const std::string& value)
    {
        std::string out = "\"";
        for (const auto ch : value)
        {
            if (ch == '"' || ch == '\\')
                out += '\\';
            if (static_cast<unsigned char>(ch) < 0x20)
                out += std::format("\\u{:04x}", static_cast<unsigned char>(ch));
            else
                out += ch;
        }
        return out + "\"";
    }
} // namespace

namespace world_converter
{
    void LightDefDumperT5::DumpAsset(AssetDumpingContext& context, const XAssetInfo<GfxLightDef>& asset)
    {
        const auto* def = asset.Asset();
        const auto file = context.OpenAssetFile(std::format("lightdef/{}.json", asset.m_name));
        if (file)
            *file << nlohmann::json({{"_game", "T5"},
                                     {"_version", 1},
                                     {"name", def->name},
                                     {"attenuation", def->attenuation.image ? def->attenuation.image->name : ""},
                                     {"samplerState", static_cast<unsigned char>(def->attenuation.samplerState)},
                                     {"lmapLookupStart", def->lmapLookupStart}})
                         .dump(2)
                  << '\n';
    }

    void ComWorldDumperT5::DumpAsset(AssetDumpingContext& context, const XAssetInfo<ComWorld>& asset)
    {
        using nlohmann::json;
        const auto* world = asset.Asset();
        json out = {{"_type", "waw2bo2_primary_lights"}, {"_game", "T5"}, {"_version", 1}, {"lights", json::array()}};
        for (unsigned int i = 0; i < world->primaryLightCount; ++i)
        {
            const auto& light = world->primaryLights[i];
            json row = {{"index", i}, {"defName", light.defName ? light.defName : ""}};
#define LIGHT_FIELD(field) row[#field] = light.field
            LIGHT_FIELD(type);
            LIGHT_FIELD(canUseShadowMap);
            LIGHT_FIELD(exponent);
            LIGHT_FIELD(priority);
            LIGHT_FIELD(cullDist);
            LIGHT_FIELD(color);
            LIGHT_FIELD(dir);
            LIGHT_FIELD(origin);
            LIGHT_FIELD(radius);
            LIGHT_FIELD(cosHalfFovOuter);
            LIGHT_FIELD(cosHalfFovInner);
            LIGHT_FIELD(cosHalfFovExpanded);
            LIGHT_FIELD(rotationLimit);
            LIGHT_FIELD(translationLimit);
            // BO1 additions, kept for later use
            LIGHT_FIELD(diffuseColor);
            LIGHT_FIELD(specularColor);
            LIGHT_FIELD(attenuation);
            LIGHT_FIELD(falloff);
            LIGHT_FIELD(angle);
            LIGHT_FIELD(aAbB);
#undef LIGHT_FIELD
            out["lights"].push_back(row);
        }
        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".primarylights.json"));
        if (file)
            *file << std::setw(2) << out << '\n';
    }

    void GfxWorldDumperT5::DumpAsset(AssetDumpingContext& context, const XAssetInfo<GfxWorld>& asset)
    {
        const auto* world = asset.Asset();
        const auto& draw = world->draw;
        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".gfx.bin"));
        if (!file)
            return;

        auto& stream = *file;
        WriteArray(stream, MAGIC.data(), MAGIC.size());
        Write(stream, uint32_t{6});
        Write(stream, draw.vertexCount);
        Write(stream, static_cast<uint32_t>(draw.indexCount));
        Write(stream, static_cast<uint32_t>(world->surfaceCount));
        Write(stream, world->dpvs.smodelCount);
        WriteString(stream, world->name);
        WriteString(stream, world->baseName);
        WriteString(stream, world->skyBoxModel);

        for (uint32_t i = 0; i < draw.vertexCount; ++i)
        {
            const auto& vertex = draw.vd.vertices[i];
            WriteArray(stream, vertex.xyz, 3);
            Write(stream, vertex.color.packed);
            WriteArray(stream, vertex.texCoord, 2);
            WriteArray(stream, vertex.lmapCoord, 2);
            Write(stream, vertex.normal.packed);
            Write(stream, vertex.tangent.packed);
            Write(stream, vertex.binormalSign);
        }
        WriteArray(stream, draw.indices, draw.indexCount);

        for (int i = 0; i < world->surfaceCount; ++i)
        {
            const auto& surface = world->dpvs.surfaces[i];
            Write(stream, surface.tris.firstVertex);
            Write(stream, surface.tris.vertexCount);
            Write(stream, surface.tris.triCount);
            Write(stream, surface.tris.baseIndex);
            WriteString(stream, MaterialName(surface.material ? surface.material->info.name : nullptr).c_str());
            Write(stream, surface.lightmapIndex);
            Write(stream, surface.reflectionProbeIndex);
            Write(stream, surface.primaryLightIndex);
            Write(stream, surface.flags);
            WriteArray(stream, surface.bounds[0], 3);
            WriteArray(stream, surface.bounds[1], 3);
        }

        for (uint32_t i = 0; i < world->dpvs.smodelCount; ++i)
        {
            const auto& model = world->dpvs.smodelDrawInsts[i];
            WriteString(stream, model.model ? model.model->name : "");
            WriteArray(stream, model.placement.origin, 3);
            WriteArray(stream, model.placement.axis[0], 9);
            Write(stream, model.placement.scale);
            Write(stream, model.flags);
            Write(stream, model.cullDist);
            Write(stream, static_cast<uint32_t>(model.primaryLightIndex));
        }

        // compiled lighting, original source data. BO1 describes the sun with GfxWorldSunColor settings; they are
        // mapped onto the WaW sun fields (sunLight / diffuseFraction / ambientScale are WaW lighting tweaks that
        // BO1 folds into the colours, so neutral values are used) and kept unchanged under "t5".
        using nlohmann::json;
        const auto& sun = world->sunParse;
        const auto& settings = sun.sunSettings[0];
        json lighting = {{"_type", "waw2bo2_lighting"},
                         {"_game", "T5"},
                         {"_version", 1},
                         {"primaryLightCount", world->primaryLightCount},
                         {"sunPrimaryLightIndex", world->sunPrimaryLightIndex},
                         {"lightmaps", json::array()}};
        auto& s = lighting["sun"];
        s["name"] = std::string(sun.name, std::find(sun.name, sun.name + sizeof(sun.name), '\0'));
        s["ambientScale"] = 1.0f;
        s["diffuseFraction"] = 0.0f;
        s["sunLight"] = settings.sunDiffuseColor[3] > 0.0f ? settings.sunDiffuseColor[3] : 1.0f;
        s["diffuseColorHasBeenSet"] = true;
        s["treeScatterIntensity"] = sun.treeScatterIntensity;
        s["treeScatterAmount"] = sun.treeScatterAmount;
        s["ambientColor"] = {settings.ambientColor[0], settings.ambientColor[1], settings.ambientColor[2]};
        s["sunColor"] = {settings.sunDiffuseColor[0], settings.sunDiffuseColor[1], settings.sunDiffuseColor[2]};
        s["diffuseColor"] = {settings.sunDiffuseColor[0], settings.sunDiffuseColor[1], settings.sunDiffuseColor[2]};
        s["angles"] = settings.angles;
        lighting["t5"] = {{"control", settings.control},
                          {"ambientColor", settings.ambientColor},
                          {"sunDiffuseColor", settings.sunDiffuseColor},
                          {"sunSpecularColor", settings.sunSpecularColor},
                          {"skyColor", settings.skyColor},
                          {"groundColor", settings.groundColor},
                          {"exposure", settings.exposure},
                          {"sunShadowSampleSizeNear", settings.sunShadowSampleSizeNear},
                          {"skyboxHDRScale", settings.skyboxHDRScale}};
        lighting["sunColorFromBsp"] = world->sunColorFromBsp;
        for (int i = 0; i < draw.lightmapCount; ++i)
        {
            const auto& lm = draw.lightmaps[i];
            lighting["lightmaps"].push_back({{"index", i},
                                             {"primary", lm.primary && lm.primary->name ? lm.primary->name : ""},
                                             {"secondary", lm.secondary && lm.secondary->name ? lm.secondary->name : ""},
                                             {"secondaryB", lm.secondaryB && lm.secondaryB->name ? lm.secondaryB->name : ""}});
        }
        const auto jsonFile = context.OpenAssetFile(OutputName(asset.m_name, ".lighting.json"));
        if (jsonFile)
            *jsonFile << std::setw(2) << lighting << '\n';

        // render ownership of brush models (the surface buffer holds world and moving brush geometry)
        Write(stream, static_cast<uint32_t>(world->modelCount));
        for (int i = 0; i < world->modelCount; ++i)
        {
            Write(stream, world->models[i].startSurfIndex);
            Write(stream, static_cast<uint32_t>(world->models[i].surfaceCount));
        }

        // the extra vertex stream of layered materials
        Write(stream, draw.vertexLayerDataSize);
        WriteArray(stream, draw.vld.data, draw.vertexLayerDataSize);
        for (int i = 0; i < world->surfaceCount; ++i)
        {
            const auto& surface = world->dpvs.surfaces[i];
            Write(stream, surface.tris.vertexLayerData);
            const auto* set = surface.material ? surface.material->techniqueSet : nullptr;
            Write(stream, set ? static_cast<uint8_t>(set->worldVertFormat) : uint8_t{0xFF});
        }

        // authored shadow casters and light-region hulls
        Write(stream, world->primaryLightCount);
        for (unsigned light = 0; light < world->primaryLightCount; ++light)
        {
            const auto* geom = world->shadowGeom ? &world->shadowGeom[light] : nullptr;
            Write(stream, geom ? geom->surfaceCount : uint16_t{0});
            Write(stream, geom ? geom->smodelCount : uint16_t{0});
            if (geom)
            {
                WriteArray(stream, geom->sortedSurfIndex, geom->surfaceCount);
                WriteArray(stream, geom->smodelIndex, geom->smodelCount);
            }
            const auto* region = world->lightRegion ? &world->lightRegion[light] : nullptr;
            Write(stream, region ? region->hullCount : 0u);
            if (region)
                for (unsigned h = 0; h < region->hullCount; ++h)
                {
                    const auto& hull = region->hulls[h];
                    WriteArray(stream, hull.kdopMidPoint, 9);
                    WriteArray(stream, hull.kdopHalfSize, 9);
                    Write(stream, hull.axisCount);
                    for (unsigned a = 0; a < hull.axisCount; ++a)
                    {
                        WriteArray(stream, hull.axis[a].dir, 3);
                        Write(stream, hull.axis[a].midPoint);
                        Write(stream, hull.axis[a].halfSize);
                    }
                }
        }

        const auto& grid = world->lightGrid;
        if (grid.rowAxis > 2 || grid.colAxis > 2 || grid.maxs[grid.rowAxis] < grid.mins[grid.rowAxis])
            throw std::runtime_error("Invalid BO1 light-grid axes/bounds");
        const auto gridFile = context.OpenAssetFile(OutputName(asset.m_name, ".lightgrid.bin"));
        if (!gridFile)
            return;
        auto& gs = *gridFile;
        constexpr std::array<char, 8> gridMagic{'W', '2', 'B', 'L', 'G', 'R', 'D', '1'};
        WriteArray(gs, gridMagic.data(), gridMagic.size());
        Write(gs, uint32_t{1});
        Write(gs, static_cast<uint32_t>(grid.hasLightRegions));
        Write(gs, grid.sunPrimaryLightIndex);
        WriteArray(gs, grid.mins, 3);
        WriteArray(gs, grid.maxs, 3);
        Write(gs, grid.rowAxis);
        Write(gs, grid.colAxis);
        const uint32_t rows = grid.rowDataStart ? grid.maxs[grid.rowAxis] - grid.mins[grid.rowAxis] + 1u : 0u;
        Write(gs, rows);
        Write(gs, grid.rawRowDataSize);
        Write(gs, grid.entryCount);
        Write(gs, grid.colorCount);
        WriteArray(gs, grid.rowDataStart, rows);
        WriteArray(gs, grid.rawRowData, grid.rawRowDataSize);
        static_assert(sizeof(GfxLightGridEntry) == 4 && sizeof(GfxCompressedLightGridColors) == 168);
        WriteArray(gs, grid.entries, grid.entryCount);
        WriteArray(gs, grid.colors, grid.colorCount);
    }

    void ClipMapDumperT5::DumpAsset(AssetDumpingContext& context, const XAssetInfo<clipMap_t>& asset)
    {
        DumpClipMap(context, asset.m_name, asset.Asset());
    }

    void ClipMapPvsDumperT5::DumpAsset(AssetDumpingContext& context, const XAssetInfo<clipMap_t>& asset)
    {
        DumpClipMap(context, asset.m_name, asset.Asset());
    }

    void PathDataDumperT5::DumpAsset(AssetDumpingContext& context, const XAssetInfo<GameWorldSp>& asset)
    {
        const auto& path = asset.Asset()->path;
        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".paths.json"));
        if (!file)
            return;

        const auto& strings = context.m_zone.m_script_strings;
        const auto str = [&strings](const unsigned idx)
        {
            return JsonString(idx && idx < strings.Count() ? strings.Value(idx) : std::string());
        };

        auto& out = *file;
        out << "{\n  \"version\": 1,\n  \"nodeCount\": " << path.nodeCount << ",\n  \"visBytes\": " << path.visBytes << ",\n  \"nodes\": [\n";
        for (auto i = 0u; i < path.nodeCount; i++)
        {
            const auto& c = path.nodes[i].constant;
            out << std::format("    {{\"type\": {}, \"spawnflags\": {}, \"targetname\": {}, \"script_linkname\": {}, \"script_noteworthy\": {}, "
                               "\"target\": {}, \"animscript\": {}, \"animscriptfunc\": {}, \"origin\": [{:.9g}, {:.9g}, {:.9g}], \"angle\": {:.9g}, "
                               "\"forward\": [{:.9g}, {:.9g}], \"radius\": {:.9g}, \"minUseDistSq\": {:.9g}, \"overlap\": [{}, {}], \"links\": [",
                               static_cast<int>(c.type),
                               c.spawnflags,
                               str(c.targetname),
                               str(c.script_linkName),
                               str(c.script_noteworthy),
                               str(c.target),
                               str(c.animscript),
                               c.animscriptfunc,
                               c.vOrigin[0],
                               c.vOrigin[1],
                               c.vOrigin[2],
                               c.fAngle,
                               c.forward[0],
                               c.forward[1],
                               c.fRadius,
                               c.minUseDistSq,
                               c.wOverlapNode[0],
                               c.wOverlapNode[1]);
            for (auto l = 0u; l < c.totalLinkCount; l++)
            {
                const auto& link = c.Links[l];
                out << std::format(
                    "{}[{}, {:.9g}, {}, {}]", l ? ", " : "", link.nodeNum, link.fDist, static_cast<int>(link.disconnectCount), static_cast<int>(link.negotiationLink));
            }
            out << "]}" << (i + 1 < path.nodeCount ? ",\n" : "\n");
        }
        out << "  ],\n  \"pathVis\": \"";
        for (auto b = 0; path.pathVis && b < path.visBytes; b++)
            out << std::format("{:02x}", static_cast<unsigned char>(path.pathVis[b]));
        out << "\"\n}\n";
    }
} // namespace world_converter
