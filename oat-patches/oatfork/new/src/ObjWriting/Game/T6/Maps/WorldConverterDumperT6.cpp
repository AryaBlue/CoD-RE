#include "WorldConverterDumperT6.h"

#include "Utils/Logging/Log.h"
#include "Utils/Pack.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <cmath>
#include <cstdint>
#include <format>
#include <map>
#include <ostream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace T6;

namespace
{
    constexpr std::array<char, 8> MAGIC{'W', '2', 'B', 'S', 'P', '0', '0', '1'};

    static_assert(sizeof(vec3_t) == 12 && sizeof(vec4_t) == 16);
    static_assert(sizeof(GfxPackedWorldVertex) == 36);

    template<typename T> void Write(std::ostream& stream, const T& value)
    {
        stream.write(reinterpret_cast<const char*>(&value), sizeof(value));
        if (!stream)
            throw std::runtime_error("Could not write T6 world interchange data");
    }

    template<typename T> void WriteArray(std::ostream& stream, const T* values, const size_t count)
    {
        if (count && !values)
            throw std::runtime_error("T6 world asset contains a null array");
        stream.write(reinterpret_cast<const char*>(values), static_cast<std::streamsize>(sizeof(T) * count));
        if (!stream)
            throw std::runtime_error("Could not write T6 world interchange array");
    }

    void WriteString(std::ostream& stream, const char* value)
    {
        // A leading comma is OAT's asset-reference marker; the interchange uses the canonical name
        const std::string text = value && value[0] == ',' ? std::string(value + 1) : (value ? value : "");
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

    // T6 packs unit vectors 10:10:10 ("third based"); the interchange reader decodes the
    // WaW layout: three biased bytes and a scale byte, (c - 127) * (s + 192) / 32385.
    // A scale byte of 63 makes that (c - 127) / 127.
    uint32_t ToWawUnitVec(const uint32_t t6Packed)
    {
        float v[3];
        pack32::Vec3UnpackUnitVecThirdBased(t6Packed, v);
        uint32_t out = 63u << 24;
        for (auto i = 0u; i < 3u; i++)
        {
            const auto c = std::lround(std::clamp(v[i], -1.0f, 1.0f) * 127.0f + 127.0f);
            out |= static_cast<uint32_t>(std::clamp<long>(c, 0, 254)) << (i * 8u);
        }
        return out;
    }

    // T6 vertex colour is R8G8B8A8 (R in the low byte); the reader expects WaW's D3DCOLOR 0xAARRGGBB
    uint32_t ToWawColor(const uint32_t t6Packed)
    {
        const auto r = t6Packed & 0xFFu;
        const auto g = (t6Packed >> 8) & 0xFFu;
        const auto b = (t6Packed >> 16) & 0xFFu;
        const auto a = (t6Packed >> 24) & 0xFFu;
        return a << 24 | r << 16 | g << 8 | b;
    }

    // Brushes owned by one cLeaf through the leaf-brush node tree (same walk as the T4 dumper)
    void CollectLeafBrushes(const clipMap_t& clip, const cLeaf_s& leaf, std::vector<uint16_t>& owned, std::set<uint16_t>& seen)
    {
        if (!leaf.brushContents || leaf.leafBrushNode < 0)
            return;

        std::vector<uint32_t> pending{static_cast<uint32_t>(leaf.leafBrushNode)};
        std::set<uint32_t> visited;
        while (!pending.empty())
        {
            const auto index = pending.back();
            pending.pop_back();
            if (index >= clip.info.leafbrushNodesCount || !visited.insert(index).second)
                continue;
            const auto& node = clip.info.leafbrushNodes[index];
            if (node.leafBrushCount > 0)
            {
                for (int16_t b = 0; b < node.leafBrushCount; ++b)
                    if (seen.insert(node.data.leaf.brushes[b]).second)
                        owned.push_back(node.data.leaf.brushes[b]);
                continue;
            }
            // Negative count: brushes crossing this split live in the following shared subtree
            if (node.leafBrushCount < 0)
                pending.push_back(index + 1);
            for (const auto offset : node.data.children.childOffset)
                if (offset)
                    pending.push_back(index + offset);
        }
    }
} // namespace

namespace world_converter
{
    GfxWorldDumperT6::GfxWorldDumperT6(const AssetPool<AssetGfxWorld::Type>& pool)
        : AbstractAssetDumper(pool)
    {
    }

    void GfxWorldDumperT6::DumpAsset(AssetDumpingContext& context, const XAssetInfo<AssetGfxWorld::Type>& asset)
    {
        const auto* world = asset.Asset();
        const auto& draw = world->draw;
        const auto* vertexData = reinterpret_cast<const char*>(draw.vd0.data);
        constexpr auto stride = sizeof(GfxPackedWorldVertex);

        // vd0 is a byte buffer of per-surface vertex blocks (36 byte stride, blocks padded to
        // 16 bytes) addressed by tris.vertexDataOffset0; indices are local to their block.
        // Surfaces share blocks and their vertexCount (often 0) does not cover the indices they
        // use. Each block is written once, compacted, sized by the highest index any of its
        // surfaces references.
        struct Block
        {
            uint32_t first = 0;
            uint32_t count = 0;
        };
        std::map<int, Block> blocks;
        for (auto i = 0; i < world->surfaceCount; ++i)
        {
            const auto& tris = world->dpvs.surfaces[i].tris;
            uint32_t referenced = tris.vertexCount;
            for (auto k = 0; k < tris.triCount * 3; ++k)
            {
                const auto index = static_cast<size_t>(tris.baseIndex) + k;
                if (index < static_cast<size_t>(draw.indexCount))
                    referenced = std::max<uint32_t>(referenced, draw.indices[index] + 1u);
            }
            auto& block = blocks[tris.vertexDataOffset0];
            block.count = std::max(block.count, referenced);
        }
        uint32_t vertexCount = 0;
        for (auto& [offset, block] : blocks)
        {
            if (offset < 0 || !vertexData || static_cast<size_t>(offset) + block.count * stride > draw.vertexDataSize0)
            {
                con::error("GfxWorld \"{}\": a surface's vertex block lies outside vd0; not writing .gfx.bin", asset.m_name);
                return;
            }
            block.first = vertexCount;
            vertexCount += block.count;
        }

        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".gfx.bin"));
        if (!file)
            return;

        auto& stream = *file;
        WriteArray(stream, MAGIC.data(), MAGIC.size());
        Write(stream, uint32_t{6});
        Write(stream, vertexCount);
        Write(stream, static_cast<uint32_t>(draw.indexCount));
        Write(stream, static_cast<uint32_t>(world->surfaceCount));
        Write(stream, world->dpvs.smodelCount);
        WriteString(stream, world->name);
        WriteString(stream, world->baseName);
        WriteString(stream, world->skyBoxModel);

        for (const auto& [offset, block] : blocks)
        {
            for (auto i = 0u; i < block.count; ++i)
            {
                GfxPackedWorldVertex vertex;
                std::memcpy(&vertex, vertexData + offset + i * stride, stride);
                float uv[2];
                pack32::Vec2UnpackTexCoordsUV(vertex.texCoord.packed, uv);
                // R16G16_UNORM (see GfxWorldLinker::LoadDrawData)
                const float lmap[2]{static_cast<float>(vertex.lmapCoord.packed & 0xFFFFu) / 65535.0f,
                                    static_cast<float>(vertex.lmapCoord.packed >> 16) / 65535.0f};
                Write(stream, vertex.xyz);
                Write(stream, ToWawColor(vertex.color.packed));
                WriteArray(stream, uv, 2);
                WriteArray(stream, lmap, 2);
                Write(stream, ToWawUnitVec(vertex.normal.packed));
                Write(stream, ToWawUnitVec(vertex.tangent.packed));
                Write(stream, vertex.binormalSign);
            }
        }
        WriteArray(stream, draw.indices, static_cast<size_t>(draw.indexCount));

        for (auto i = 0; i < world->surfaceCount; ++i)
        {
            const auto& surface = world->dpvs.surfaces[i];
            const auto& block = blocks.at(surface.tris.vertexDataOffset0);
            Write(stream, block.first);
            Write(stream, static_cast<uint16_t>(std::min<uint32_t>(block.count, 0xFFFFu)));
            Write(stream, surface.tris.triCount);
            Write(stream, static_cast<uint32_t>(surface.tris.baseIndex));
            WriteString(stream, surface.material ? surface.material->info.name : "");
            Write(stream, surface.lightmapIndex);
            Write(stream, surface.reflectionProbeIndex);
            Write(stream, surface.primaryLightIndex);
            Write(stream, surface.flags);
            Write(stream, surface.bounds[0]);
            Write(stream, surface.bounds[1]);
        }

        for (auto i = 0u; i < world->dpvs.smodelCount; ++i)
        {
            const auto& model = world->dpvs.smodelDrawInsts[i];
            WriteString(stream, model.model ? model.model->name : "");
            Write(stream, model.placement.origin);
            WriteArray(stream, model.placement.axis, 3);
            Write(stream, model.placement.scale);
            Write(stream, static_cast<uint32_t>(model.flags));
            Write(stream, model.cullDist);                                                      // v2
            Write(stream, static_cast<uint32_t>(static_cast<uint8_t>(model.primaryLightIndex))); // v3
        }

        // v4: render surface ranges per brush model; model 0 is the world
        Write(stream, static_cast<uint32_t>(world->modelCount));
        for (auto i = 0; i < world->modelCount; ++i)
        {
            Write(stream, world->models[i].startSurfIndex);
            Write(stream, world->models[i].surfaceCount);
        }

        // v5: WaW layered-material vertex stream. T6 layer data (vd1) has a different
        // per-format layout, so it is not exported: an empty buffer, no format per surface.
        Write(stream, uint32_t{0});
        for (auto i = 0; i < world->surfaceCount; ++i)
        {
            Write(stream, int32_t{0});
            Write(stream, uint8_t{0xFF});
        }

        // v6: shadow casters and light-region hulls per primary light
        Write(stream, world->primaryLightCount);
        for (auto light = 0u; light < world->primaryLightCount; ++light)
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
            {
                for (auto h = 0u; h < region->hullCount; ++h)
                {
                    const auto& hull = region->hulls[h];
                    WriteArray(stream, hull.kdopMidPoint, 9);
                    WriteArray(stream, hull.kdopHalfSize, 9);
                    Write(stream, hull.axisCount);
                    for (auto a = 0u; a < hull.axisCount; ++a)
                    {
                        Write(stream, hull.axis[a].dir);
                        Write(stream, hull.axis[a].midPoint);
                        Write(stream, hull.axis[a].halfSize);
                    }
                }
            }
        }
    }

    ClipMapDumperT6::ClipMapDumperT6(const AssetPool<AssetClipMap::Type>& pool)
        : AbstractAssetDumper(pool)
    {
    }

    void ClipMapDumperT6::DumpAsset(AssetDumpingContext& context, const XAssetInfo<AssetClipMap::Type>& asset)
    {
        const auto* clip = asset.Asset();
        const auto& info = clip->info;

        // T6 brush sides carry content/surface flags, not a material index. The interchange
        // stores an index into its material table, and the bridge turns it back into flags,
        // so every side gets a material with exactly its flags; missing pairs are appended.
        std::vector<std::pair<std::string, std::pair<int, int>>> materials; // name, (surfaceFlags, contentFlags)
        std::map<std::pair<int, int>, uint32_t> materialByFlags;
        for (auto i = 0u; i < info.numMaterials; ++i)
        {
            const auto& material = info.materials[i];
            const auto name = material.name && material.name[0] == ',' ? material.name + 1 : (material.name ? material.name : "");
            materials.emplace_back(name, std::make_pair(material.surfaceFlags, material.contentFlags));
            materialByFlags.emplace(std::make_pair(material.surfaceFlags, material.contentFlags), i);
        }
        auto synthesized = 0u;
        const auto materialFor = [&](const int cflags, const int sflags)
        {
            const auto key = std::make_pair(sflags, cflags);
            if (const auto found = materialByFlags.find(key); found != materialByFlags.end())
                return found->second;
            const auto index = static_cast<uint32_t>(materials.size());
            materials.emplace_back(std::format("$t6_clipflags_c{:08x}_s{:08x}", static_cast<uint32_t>(cflags), static_cast<uint32_t>(sflags)), key);
            materialByFlags.emplace(key, index);
            synthesized++;
            return index;
        };

        struct Side
        {
            float x, y, z, dist;
            uint32_t material;
        };
        std::vector<std::vector<Side>> brushSides(info.numBrushes);
        for (auto i = 0u; i < info.numBrushes; ++i)
        {
            const auto& brush = info.brushes[i];
            auto& sides = brushSides[i];
            // axial planes in -x,+x,-y,+y,-z,+z order; [0] holds the min sides, [1] the max sides
            for (auto axis = 0u; axis < 3u; ++axis)
            {
                const float* mins = &brush.mins.x;
                const float* maxs = &brush.maxs.x;
                float normal[3]{};
                normal[axis] = -1.0f;
                sides.push_back({normal[0], normal[1], normal[2], -mins[axis], materialFor(brush.axial_cflags[0][axis], brush.axial_sflags[0][axis])});
                normal[axis] = 1.0f;
                sides.push_back({normal[0], normal[1], normal[2], maxs[axis], materialFor(brush.axial_cflags[1][axis], brush.axial_sflags[1][axis])});
            }
            for (auto s = 0u; s < brush.numsides; ++s)
            {
                const auto& side = brush.sides[s];
                if (!side.plane)
                    throw std::runtime_error("T6 brush contains a null side plane");
                sides.push_back({side.plane->normal.x, side.plane->normal.y, side.plane->normal.z, side.plane->dist, materialFor(side.cflags, side.sflags)});
            }
        }
        if (synthesized)
            con::info("{}: {} brush side flag combinations have no clip material; added synthetic entries", asset.m_name, synthesized);

        const auto file = context.OpenAssetFile(OutputName(asset.m_name, ".clip.bin"));
        if (!file)
            return;

        auto& stream = *file;
        WriteArray(stream, MAGIC.data(), MAGIC.size());
        Write(stream, uint32_t{9});
        WriteString(stream, clip->name);
        Write(stream, static_cast<uint32_t>(materials.size()));
        for (const auto& [name, flags] : materials)
        {
            WriteString(stream, name.c_str());
            Write(stream, flags.first);
            Write(stream, flags.second);
        }

        Write(stream, clip->vertCount);
        WriteArray(stream, clip->verts, clip->vertCount);
        Write(stream, static_cast<uint32_t>(clip->triCount));
        WriteArray(stream, clip->triIndices, static_cast<size_t>(clip->triCount));

        Write(stream, static_cast<uint32_t>(info.numBrushes));
        for (auto i = 0u; i < info.numBrushes; ++i)
        {
            const auto& brush = info.brushes[i];
            Write(stream, brush.mins);
            Write(stream, brush.maxs);
            Write(stream, brush.contents);
            Write(stream, static_cast<uint32_t>(brushSides[i].size()));
            for (const auto& side : brushSides[i])
                WritePlane(stream, side.x, side.y, side.z, side.dist, side.material);
            Write(stream, brush.numverts);
            WriteArray(stream, brush.verts, brush.numverts);
        }

        // v3: brushes reachable from each submodel; cmodel 0 is the world and owns what its leafs reference
        Write(stream, clip->numSubModels);
        for (auto i = 0u; i < clip->numSubModels; ++i)
        {
            const auto& model = clip->cmodels[i];
            Write(stream, model.mins);
            Write(stream, model.maxs);

            std::vector<uint16_t> owned;
            std::set<uint16_t> seen;
            if (i == 0)
            {
                // T6 world leafs also reach the brushes of brush models (doors, movers); those
                // belong to their entity, never to static world collision
                for (auto sub = 1u; sub < clip->numSubModels; ++sub)
                {
                    std::vector<uint16_t> entityBrushes;
                    CollectLeafBrushes(*clip, clip->cmodels[sub].leaf, entityBrushes, seen);
                }
                for (auto leaf = 0u; leaf < clip->numLeafs; ++leaf)
                    CollectLeafBrushes(*clip, clip->leafs[leaf], owned, seen);
            }
            else
                CollectLeafBrushes(*clip, model.leaf, owned, seen);
            std::erase_if(owned, [&info](const uint16_t b) { return b >= info.numBrushes; });
            Write(stream, static_cast<uint32_t>(owned.size()));
            WriteArray(stream, owned.data(), owned.size());
        }

        // v3: collidable static models with their model-space collision hulls
        Write(stream, clip->numStaticModels);
        for (auto i = 0u; i < clip->numStaticModels; ++i)
        {
            const auto& sm = clip->staticModelList[i];
            const auto* model = sm.xmodel;
            WriteString(stream, model ? model->name : "");
            Write(stream, sm.origin);
            WriteArray(stream, sm.invScaledAxis, 3);
            Write(stream, sm.absmin);
            Write(stream, sm.absmax);
            Write(stream, model ? model->contents : 0);
            const auto surfCount = model && model->collSurfs ? static_cast<uint32_t>(model->numCollSurfs) : 0u;
            Write(stream, surfCount);
            for (auto s = 0u; s < surfCount; ++s)
            {
                const auto& surf = model->collSurfs[s];
                Write(stream, surf.contents);
                Write(stream, surf.surfFlags);
                Write(stream, surf.mins);
                Write(stream, surf.maxs);
                Write(stream, surf.boneIdx);
                Write(stream, static_cast<uint32_t>(surf.numCollTris));
                for (auto t = 0; t < surf.numCollTris; ++t)
                {
                    Write(stream, surf.collTris[t].plane);
                    Write(stream, surf.collTris[t].svec);
                    Write(stream, surf.collTris[t].tvec);
                }
            }
        }

        // v4: clip material of every collision triangle, from the leaf aabb nodes' partitions
        std::vector<uint16_t> triMaterial(static_cast<size_t>(clip->triCount), 0xFFFF);
        for (auto a = 0; a < clip->aabbTreeCount; ++a)
        {
            const auto& tree = clip->aabbTrees[a];
            if (tree.childCount != 0 || tree.u.partitionIndex < 0 || tree.u.partitionIndex >= clip->partitionCount
                || tree.materialIndex >= info.numMaterials)
                continue;
            const auto& partition = clip->partitions[tree.u.partitionIndex];
            for (auto t = 0; t < static_cast<uint8_t>(partition.triCount); ++t)
            {
                const auto tri = static_cast<size_t>(partition.firstTri + t);
                if (tri < triMaterial.size())
                    triMaterial[tri] = tree.materialIndex;
            }
        }
        Write(stream, static_cast<uint32_t>(triMaterial.size()));
        WriteArray(stream, triMaterial.data(), triMaterial.size());

        // v6: one walkable bit per triangle edge
        const auto edgeBytes = static_cast<uint32_t>((3 * clip->triCount + 31) / 32 * 4);
        Write(stream, edgeBytes);
        if (edgeBytes && clip->triEdgeIsWalkable)
            WriteArray(stream, clip->triEdgeIsWalkable, edgeBytes);
        else
            for (auto i = 0u; i < edgeBytes; ++i)
                Write(stream, uint8_t{0xFF});

        // v7: terrain aabb tree, collision leaf roots and partitions
        Write(stream, static_cast<uint32_t>(clip->aabbTreeCount));
        for (auto a = 0; a < clip->aabbTreeCount; ++a)
        {
            const auto& tree = clip->aabbTrees[a];
            Write(stream, tree.materialIndex);
            Write(stream, tree.childCount);
            Write(stream, tree.u.firstChildIndex);
        }
        Write(stream, clip->numLeafs);
        for (auto l = 0u; l < clip->numLeafs; ++l)
        {
            Write(stream, static_cast<uint32_t>(clip->leafs[l].firstCollAabbIndex));
            Write(stream, static_cast<uint32_t>(clip->leafs[l].collAabbCount));
            Write(stream, clip->leafs[l].terrainContents);
        }
        Write(stream, static_cast<uint32_t>(clip->partitionCount));
        for (auto p = 0; p < clip->partitionCount; ++p)
        {
            Write(stream, static_cast<uint32_t>(clip->partitions[p].firstTri));
            Write(stream, static_cast<uint32_t>(static_cast<uint8_t>(clip->partitions[p].triCount)));
        }

        // v8: effective brush masks reached through all authored leaf trees
        std::vector<int> reach(info.numBrushes, 0);
        const auto visitLeaf = [&](const cLeaf_s& leaf)
        {
            std::vector<std::pair<uint32_t, int>> pending;
            std::set<std::pair<uint32_t, int>> visited;
            if (leaf.brushContents && leaf.leafBrushNode >= 0)
                pending.emplace_back(static_cast<uint32_t>(leaf.leafBrushNode), leaf.brushContents);
            while (!pending.empty())
            {
                const auto [index, inherited] = pending.back();
                pending.pop_back();
                if (index >= info.leafbrushNodesCount || !visited.emplace(index, inherited).second)
                    continue;
                const auto& node = info.leafbrushNodes[index];
                const int mask = inherited & node.contents;
                if (node.leafBrushCount > 0)
                {
                    for (int b = 0; b < node.leafBrushCount; b++)
                    {
                        const auto brush = node.data.leaf.brushes[b];
                        if (brush < info.numBrushes)
                            reach[brush] |= mask & info.brushes[brush].contents;
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
        for (auto i = 0u; i < clip->numLeafs; i++)
            visitLeaf(clip->leafs[i]);
        for (auto i = 1u; i < clip->numSubModels; i++)
            visitLeaf(clip->cmodels[i].leaf);
        Write(stream, static_cast<uint32_t>(info.numBrushes));
        WriteArray(stream, reach.data(), reach.size());

        // v9: terrain roots of every cmodel
        Write(stream, clip->numSubModels);
        for (auto i = 0u; i < clip->numSubModels; i++)
        {
            const auto& leaf = clip->cmodels[i].leaf;
            Write(stream, static_cast<uint32_t>(leaf.firstCollAabbIndex));
            Write(stream, static_cast<uint32_t>(leaf.collAabbCount));
            Write(stream, leaf.terrainContents);
        }
    }
} // namespace world_converter
