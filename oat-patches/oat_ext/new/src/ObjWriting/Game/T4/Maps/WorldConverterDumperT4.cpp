#include "WorldConverterDumperT4.h"

#include <array>
#include <algorithm>
#include <cstdint>
#include <format>
#include <ostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include <iomanip>
#include <nlohmann/json.hpp>

using namespace T4;

namespace
{
    constexpr std::array<char, 8> MAGIC{'W', '2', 'B', 'S', 'P', '0', '0', '1'};

    template <typename T> void Write(std::ostream& stream, const T& value)
    {
        stream.write(reinterpret_cast<const char*>(&value), sizeof(value));
        if (!stream)
            throw std::runtime_error("Could not write WaW world interchange data");
    }

    template <typename T> void WriteArray(std::ostream& stream, const T* values, const size_t count)
    {
        if (count && !values)
            throw std::runtime_error("WaW world asset contains a null array");
        stream.write(reinterpret_cast<const char*>(values), static_cast<std::streamsize>(sizeof(T) * count));
        if (!stream)
            throw std::runtime_error("Could not write WaW world interchange array");
    }

    void WriteString(std::ostream& stream, const char* value)
    {
        // A leading comma is OAT's internal asset-reference marker. Material
        // dumpers remove it before writing JSON, so the world interchange
        // format must use the same canonical asset name.
        const std::string text = value && value[0] == ',' ? std::string(value + 1) : (value ? value : "");
        if (text.size() > UINT32_MAX)
            throw std::runtime_error("WaW asset name is too long");
        Write(stream, static_cast<uint32_t>(text.size()));
        stream.write(text.data(), static_cast<std::streamsize>(text.size()));
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
} // namespace

namespace world_converter
{
    void LightDefDumperT4::DumpAsset(AssetDumpingContext& context, const XAssetInfo<GfxLightDef>& asset)
    {
        const auto* def = asset.Asset();
        const auto file = context.OpenAssetFile(std::format("lightdef/{}.json", asset.m_name));
        if (file)
            *file << nlohmann::json({{"_game", "T4"}, {"_version", 1},
                {"name", def->name}, {"attenuation", def->attenuation.image ? def->attenuation.image->name : ""},
                {"samplerState", static_cast<unsigned char>(def->attenuation.samplerState)},
                {"lmapLookupStart", def->lmapLookupStart}}).dump(2) << '\n';
    }
    void ComWorldDumperT4::DumpAsset(AssetDumpingContext& context, const XAssetInfo<ComWorld>& asset)
    {
        using nlohmann::json;
        const auto* world = asset.Asset();
        json out = {{"_type", "waw2bo2_primary_lights"}, {"_game", "T4"}, {"_version", 1},
                    {"lights", json::array()}};
        for (unsigned int i = 0; i < world->primaryLightCount; ++i)
        {
            const auto& light = world->primaryLights[i];
            json row = {{"index", i}, {"defName", light.defName ? light.defName : ""}};
#define LIGHT_FIELD(field) row[#field] = light.field
            LIGHT_FIELD(type); LIGHT_FIELD(canUseShadowMap); LIGHT_FIELD(exponent); LIGHT_FIELD(priority);
            LIGHT_FIELD(cullDist); LIGHT_FIELD(color); LIGHT_FIELD(dir); LIGHT_FIELD(origin);
            LIGHT_FIELD(radius); LIGHT_FIELD(cosHalfFovOuter); LIGHT_FIELD(cosHalfFovInner);
            LIGHT_FIELD(cosHalfFovExpanded); LIGHT_FIELD(rotationLimit); LIGHT_FIELD(translationLimit);
#undef LIGHT_FIELD
            out["lights"].push_back(row);
        }
        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".primarylights.json"));
        if (file) *file << std::setw(2) << out << '\n';
    }

    void GfxWorldDumperT4::DumpAsset(AssetDumpingContext& context, const XAssetInfo<GfxWorld>& asset)
    {
        const auto* world = asset.Asset();
        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".gfx.bin"));
        if (!file)
            return;

        auto& stream = *file;
        WriteArray(stream, MAGIC.data(), MAGIC.size());
        Write(stream, uint32_t{6});
        Write(stream, world->vertexCount);
        Write(stream, static_cast<uint32_t>(world->indexCount));
        Write(stream, static_cast<uint32_t>(world->surfaceCount));
        Write(stream, world->dpvs.smodelCount);
        WriteString(stream, world->name);
        WriteString(stream, world->baseName);
        WriteString(stream, world->skyBoxModel);

        for (uint32_t i = 0; i < world->vertexCount; ++i)
        {
            const auto& vertex = world->vd.vertices[i];
            WriteArray(stream, vertex.xyz, 3);
            Write(stream, vertex.color.packed);
            WriteArray(stream, vertex.texCoord, 2);
            WriteArray(stream, vertex.lmapCoord, 2);
            Write(stream, vertex.normal.packed);
            Write(stream, vertex.tangent.packed);
            Write(stream, vertex.binormalSign);
        }
        WriteArray(stream, world->indices, world->indexCount);

        for (int i = 0; i < world->surfaceCount; ++i)
        {
            const auto& surface = world->dpvs.surfaces[i];
            Write(stream, surface.tris.firstVertex);
            Write(stream, surface.tris.vertexCount);
            Write(stream, surface.tris.triCount);
            Write(stream, surface.tris.baseIndex);
            WriteString(stream, surface.material ? surface.material->info.name : "");
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
            Write(stream, model.cullDist); // v2
            Write(stream, static_cast<uint32_t>(model.primaryLightIndex)); // v3
        }

        // Keep compiled lighting independently of the geometry interchange.
        // T4 and T6 shader encodings differ: these are ORIGINAL source data,
        // not a claim that copying a lightmap into T6 produces correct light.
        using nlohmann::json;
        const auto& sun = world->sunParse;
        json lighting = {{"_type", "waw2bo2_lighting"}, {"_game", "T4"}, {"_version", 1},
                         {"primaryLightCount", world->primaryLightCount},
                         {"sunPrimaryLightIndex", world->sunPrimaryLightIndex}, {"lightmaps", json::array()}};
        auto& s = lighting["sun"];
        s["name"] = std::string(sun.name, std::find(sun.name, sun.name + sizeof(sun.name), '\0'));
        s["ambientScale"] = sun.ambientScale;
        s["diffuseFraction"] = sun.diffuseFraction;
        s["sunLight"] = sun.sunLight;
        s["diffuseColorHasBeenSet"] = sun.diffuseColorHasBeenSet;
        s["treeScatterIntensity"] = sun.treeScatterIntensity;
        s["treeScatterAmount"] = sun.treeScatterAmount;
        s["ambientColor"] = sun.ambientColor;
        s["sunColor"] = sun.sunColor;
        s["diffuseColor"] = sun.diffuseColor;
        s["angles"] = sun.angles;
        lighting["sunColorFromBsp"] = world->sunColorFromBsp;
        for (int i = 0; i < world->lightmapCount; ++i)
        {
            const auto& lm = world->lightmaps[i];
            lighting["lightmaps"].push_back({{"index", i},
                {"primary", lm.primary && lm.primary->name ? lm.primary->name : ""},
                {"secondary", lm.secondary && lm.secondary->name ? lm.secondary->name : ""}});
        }
        const auto jsonFile = context.OpenAssetFile(OutputName(asset.m_name, ".lighting.json"));
        if (jsonFile) *jsonFile << std::setw(2) << lighting << '\n';

        // Preserve render ownership independently of collision submodel bounds.
        // The same surface buffer contains world and moving brush geometry.
        Write(stream, static_cast<uint32_t>(world->modelCount));
        for (int i = 0; i < world->modelCount; ++i)
        {
            Write(stream, world->models[i].startSurfIndex);
            Write(stream, static_cast<uint32_t>(world->models[i].surfaceCount));
        }

        // v5: preserve the extra vertex stream used by layered materials.
        Write(stream, world->vertexLayerDataSize);
        WriteArray(stream, world->vld.data, world->vertexLayerDataSize);
        for (int i = 0; i < world->surfaceCount; ++i) {
            const auto& surface = world->dpvs.surfaces[i];
            Write(stream, surface.tris.vertexLayerData);
            const auto* set = surface.material ? surface.material->techniqueSet : nullptr;
            Write(stream, set ? static_cast<uint8_t>(set->worldVertFormat) : uint8_t{0xFF});
        }
        // v6: authored shadow casters and light-region hulls.
        Write(stream, world->primaryLightCount);
        for (unsigned light = 0; light < world->primaryLightCount; ++light) {
            const auto* geom = world->shadowGeom ? &world->shadowGeom[light] : nullptr;
            Write(stream, geom ? geom->surfaceCount : uint16_t{0});
            Write(stream, geom ? geom->smodelCount : uint16_t{0});
            if (geom) {
                WriteArray(stream, geom->sortedSurfIndex, geom->surfaceCount);
                WriteArray(stream, geom->smodelIndex, geom->smodelCount);
            }
            const auto* region = world->lightRegion ? &world->lightRegion[light] : nullptr;
            Write(stream, region ? region->hullCount : 0u);
            if (region) for (unsigned h = 0; h < region->hullCount; ++h) {
                const auto& hull = region->hulls[h];
                WriteArray(stream, hull.kdopMidPoint, 9);
                WriteArray(stream, hull.kdopHalfSize, 9);
                Write(stream, hull.axisCount);
                for (unsigned a = 0; a < hull.axisCount; ++a) {
                    WriteArray(stream, hull.axis[a].dir, 3);
                    Write(stream, hull.axis[a].midPoint);
                    Write(stream, hull.axis[a].halfSize);
                }
            }
        }

        const auto& grid = world->lightGrid;
        if (grid.rowAxis > 2 || grid.colAxis > 2 || grid.maxs[grid.rowAxis] < grid.mins[grid.rowAxis])
            throw std::runtime_error("Invalid WaW light-grid axes/bounds");
        const auto gridFile = context.OpenAssetFile(OutputName(asset.m_name, ".lightgrid.bin"));
        if (!gridFile) return;
        auto& gs = *gridFile;
        constexpr std::array<char, 8> gridMagic{'W','2','B','L','G','R','D','1'};
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
        static_assert(sizeof(GfxLightGridEntry) == 4 && sizeof(GfxLightGridColors) == 168);
        WriteArray(gs, grid.entries, grid.entryCount);
        WriteArray(gs, grid.colors, grid.colorCount);
    }

    void ClipMapDumperT4::DumpAsset(AssetDumpingContext& context, const XAssetInfo<clipMap_t>& asset)
    {
        const auto* clip = asset.Asset();

        // Preserve authored map physics joints and their rendered ropes.
        const auto constraintFile = context.OpenAssetFile(OutputName(asset.m_name, ".constraints.json"));
        if (constraintFile) {
            const auto& strings = context.m_zone.m_script_strings;
            const auto str = [&strings](unsigned id) { return id && id < strings.Count() ? strings.Value(id) : std::string(); };
            const auto vec = [](const float* v) { return nlohmann::json::array({v[0],v[1],v[2]}); };
            nlohmann::json entries = nlohmann::json::array();
            for(int i=0;i<clip->num_constraints;i++) {
                const auto& c=clip->constraints[i];
                nlohmann::json j={{"targetname",str(c.targetname)},{"type",static_cast<int>(c.type)},
                    {"attach_point_type1",static_cast<int>(c.attach_point_type1)},{"target_index1",c.target_index1},
                    {"target_ent1",str(c.target_ent1)},{"target_bone1",c.target_bone1?c.target_bone1:""},
                    {"attach_point_type2",static_cast<int>(c.attach_point_type2)},{"target_index2",c.target_index2},
                    {"target_ent2",str(c.target_ent2)},{"target_bone2",c.target_bone2?c.target_bone2:""},
                    {"offset",vec(c.offset)},{"pos",vec(c.pos)},{"pos2",vec(c.pos2)},{"dir",vec(c.dir)},
                    {"flags",c.flags},{"timeout",c.timeout},{"min_health",c.min_health},{"max_health",c.max_health},
                    {"distance",c.distance},{"damp",c.damp},{"power",c.power},{"scale",vec(c.scale)},
                    {"spin_scale",c.spin_scale},{"minAngle",c.minAngle},{"maxAngle",c.maxAngle},
                    {"material",c.material&&c.material->info.name?c.material->info.name:""},
                    {"constraintHandle",c.constraintHandle},{"rope_index",c.rope_index}};
                entries.push_back(std::move(j));
            }
            *constraintFile << nlohmann::json({{"version",1},{"constraints",entries}}).dump(2);
        }

        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".clip.bin"));
        if (!file)
            return;

        auto& stream = *file;
        WriteArray(stream, MAGIC.data(), MAGIC.size());
        // v5 has the v4 payload, but guarantees shared leaf-brush branches
        // were visited. Readers must not guess ownership from local bounds.
        // v6 appends the compiled walkable bit of every triangle edge.
        // v7 appends the terrain aabb tree and the collision leafs' roots.
        Write(stream, uint32_t{9});
        WriteString(stream, clip->name);
        Write(stream, clip->numMaterials);
        for (uint32_t i = 0; i < clip->numMaterials; ++i)
        {
            WriteString(stream, clip->materials[i].material);
            Write(stream, clip->materials[i].surfaceFlags);
            Write(stream, clip->materials[i].contentFlags);
        }

        Write(stream, clip->vertCount);
        WriteArray(stream, clip->verts, clip->vertCount);
        Write(stream, static_cast<uint32_t>(clip->triCount));
        WriteArray(stream, clip->triIndices, static_cast<size_t>(clip->triCount) * 3);

        Write(stream, static_cast<uint32_t>(clip->numBrushes));
        for (uint32_t i = 0; i < clip->numBrushes; ++i)
        {
            const auto& brush = clip->brushes[i];
            WriteArray(stream, brush.mins, 3);
            WriteArray(stream, brush.maxs, 3);
            Write(stream, brush.contents);
            Write(stream, static_cast<uint32_t>(brush.numsides + 6));

            WritePlane(stream, -1.0f, 0.0f, 0.0f, -brush.mins[0], static_cast<uint16_t>(brush.axialMaterialNum[0][0]));
            WritePlane(stream, 1.0f, 0.0f, 0.0f, brush.maxs[0], static_cast<uint16_t>(brush.axialMaterialNum[1][0]));
            WritePlane(stream, 0.0f, -1.0f, 0.0f, -brush.mins[1], static_cast<uint16_t>(brush.axialMaterialNum[0][1]));
            WritePlane(stream, 0.0f, 1.0f, 0.0f, brush.maxs[1], static_cast<uint16_t>(brush.axialMaterialNum[1][1]));
            WritePlane(stream, 0.0f, 0.0f, -1.0f, -brush.mins[2], static_cast<uint16_t>(brush.axialMaterialNum[0][2]));
            WritePlane(stream, 0.0f, 0.0f, 1.0f, brush.maxs[2], static_cast<uint16_t>(brush.axialMaterialNum[1][2]));
            for (uint32_t side = 0; side < brush.numsides; ++side)
            {
                const auto& source = brush.sides[side];
                if (!source.plane)
                    throw std::runtime_error("WaW brush contains a null side plane");
                WritePlane(stream, source.plane->normal[0], source.plane->normal[1], source.plane->normal[2], source.plane->dist, source.materialNum);
            }

            Write(stream, brush.numverts);
            WriteArray(stream, brush.verts, brush.numverts);
        }

        // v3: brushes reachable from each submodel. cmodel 0 is the world and
        // owns what its BSP leafs reference; brush models (doors, blockers)
        // belong to entities and must not become static world collision.
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
                // Negative count: brushes crossing this split are held in
                // the immediately following shared subtree, before children.
                if (node.leafBrushCount < 0)
                    pending.push_back(index + 1);
                for (const auto offset : node.data.children.childOffset)
                    if (offset)
                        pending.push_back(index + offset);
            }
            Write(stream, static_cast<uint32_t>(owned.size()));
            WriteArray(stream, owned.data(), owned.size());
        }

        // v3: collidable static models with their model-space collision hulls
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
                // each collTri is one triangle: its plane plus the s/t barycentric vectors
                for (int t = 0; t < surf.numCollTris; ++t)
                {
                    WriteArray(stream, surf.collTris[t].plane, 4);
                    WriteArray(stream, surf.collTris[t].svec, 4);
                    WriteArray(stream, surf.collTris[t].tvec, 4);
                }
            }
        }

        // v4: clip material of every collision triangle. WaW keeps it on the
        // leaf aabb nodes (childCount 0 -> partition -> triangles); decals and
        // other non-solid surfaces (contents 0) live in the same triangle soup.
        std::vector<uint16_t> triMaterial(static_cast<size_t>(clip->triCount), 0xFFFF);
        for (int a = 0; a < clip->aabbTreeCount; ++a)
        {
            const auto& tree = clip->aabbTrees[a];
            if (tree.childCount != 0 || tree.u.partitionIndex < 0 || tree.u.partitionIndex >= clip->partitionCount)
                continue;
            const auto& partition = clip->partitions[tree.u.partitionIndex];
            for (int t = 0; t < partition.triCount; ++t)
            {
                const auto tri = static_cast<size_t>(partition.firstTri + t);
                if (tri < triMaterial.size())
                    triMaterial[tri] = tree.materialIndex;
            }
        }
        Write(stream, static_cast<uint32_t>(triMaterial.size()));
        WriteArray(stream, triMaterial.data(), triMaterial.size());

        // v6: triEdgeIsWalkable, one bit per edge (3 * triCount bits, edge e of
        // triangle t is bit 3t+e). Contacts on a set edge count as ground
        // regardless of slope, so the compiler's bits must survive conversion.
        const auto edgeBytes = static_cast<uint32_t>((3 * clip->triCount + 31) / 32 * 4);
        Write(stream, edgeBytes);
        if (edgeBytes && clip->triEdgeIsWalkable)
            WriteArray(stream, clip->triEdgeIsWalkable, edgeBytes);
        else
            for (uint32_t i = 0; i < edgeBytes; ++i)
                Write(stream, uint8_t{0xFF});

        // v7: the terrain aabb tree. Traces test a node's clip material against
        // their mask before its children, so a triangle collides with a mask
        // only if every node on its path does; the leaf material alone is not
        // the triangle's effective contents.
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
        // v8: effective brush masks reached through all authored leaf trees.
        std::vector<int> reach(clip->numBrushes, 0);
        const auto visitLeaf = [&](const cLeaf_t& leaf)
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

        // v9: terrain in a moving cmodel is not owned by the world's BSP leafs.
        Write(stream, clip->numSubModels);
        for (uint32_t i = 0; i < clip->numSubModels; i++)
        {
            const auto& leaf = clip->cmodels[i].leaf;
            Write(stream, static_cast<uint32_t>(leaf.firstCollAabbIndex));
            Write(stream, static_cast<uint32_t>(leaf.collAabbCount));
            Write(stream, leaf.terrainContents);
        }
    }
    namespace
    {
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

    void PathDataDumperT4::DumpAsset(AssetDumpingContext& context, const XAssetInfo<GameWorldSp>& asset)
    {
        const auto& path = asset.Asset()->path;
        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".paths.json"));
        if (!file)
            return;

        const auto& strings = context.m_zone.m_script_strings;
        const auto str = [&strings](const unsigned idx) { return JsonString(idx && idx < strings.Count() ? strings.Value(idx) : std::string()); };

        auto& out = *file;
        out << "{\n  \"version\": 1,\n  \"nodeCount\": " << path.nodeCount << ",\n  \"visBytes\": " << path.visBytes << ",\n  \"nodes\": [\n";
        for (auto i = 0u; i < path.nodeCount; i++)
        {
            const auto& c = path.nodes[i].constant;
            out << std::format("    {{\"type\": {}, \"spawnflags\": {}, \"targetname\": {}, \"script_linkname\": {}, \"script_noteworthy\": {}, "
                               "\"target\": {}, \"animscript\": {}, \"animscriptfunc\": {}, \"origin\": [{:.9g}, {:.9g}, {:.9g}], \"angle\": {:.9g}, "
                               "\"forward\": [{:.9g}, {:.9g}], \"radius\": {:.9g}, \"minUseDistSq\": {:.9g}, \"overlap\": [{}, {}], \"links\": [",
                               static_cast<int>(c.type), c.spawnflags, str(c.targetname), str(c.script_linkName), str(c.script_noteworthy), str(c.target),
                               str(c.animscript), c.animscriptfunc, c.vOrigin[0], c.vOrigin[1], c.vOrigin[2], c.fAngle, c.forward[0], c.forward[1], c.fRadius,
                               c.minUseDistSq, c.wOverlapNode[0], c.wOverlapNode[1]);
            for (auto l = 0u; l < c.totalLinkCount; l++)
            {
                const auto& link = c.Links[l];
                out << std::format("{}[{}, {:.9g}, {}, {}]", l ? ", " : "", link.nodeNum, link.fDist, static_cast<int>(link.disconnectCount),
                                   static_cast<int>(link.negotiationLink));
            }
            out << "]}" << (i + 1 < path.nodeCount ? ",\n" : "\n");
        }
        out << "  ],\n  \"pathVis\": \"";
        for (auto b = 0; path.pathVis && b < path.visBytes; b++)
            out << std::format("{:02x}", static_cast<unsigned char>(path.pathVis[b]));
        out << "\"\n}\n";
    }
} // namespace world_converter
