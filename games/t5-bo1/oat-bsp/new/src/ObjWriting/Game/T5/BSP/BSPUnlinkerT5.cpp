// Black Ops (T5) world assets -> T6::BSP::BSPData.
// Adapted from Game/T6/BSP/BSPUnlinker.cpp; the T5 structs keep most collision data directly in clipMap_t
// (no ClipInfo), store world vertices as an indexed 44-byte GfxWorldVertex array, and group surfaces as lit/decal/emissive.

#include "BSPUnlinkerT5.h"

#include "BSP/BSPUtil.h"
#include "Game/T5/CommonT5.h"

#include <QuickHull.hpp>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <deque>
#include <format>
#include <fstream>
#include <iterator>
#include <map>
#include <unordered_map>
#include <unordered_set>
#include <cstdio>

#define T5BSP_TRACE(...) do { fprintf(stderr, "[t5bsp] " __VA_ARGS__); fputc(10, stderr); fflush(stderr); } while (0)

using namespace T6::BSP;
using namespace quickhull;

namespace
{
    using T6::vec2_t;
    using T6::vec3_t;
    using T6::vec4_t;

    constexpr vec4_t whiteColour = {1.0f, 1.0f, 1.0f, 1.0f};

    // T6 GfxSurfaceFlags kept by the BSP linker
    constexpr int SURF_CASTS_SUN_SHADOW = 0x1;
    constexpr int SURF_IS_SKY = 0x4;
    constexpr int SURF_NO_DRAW = 0x8;

    // T5 GfxLightType (no SPOT_SQUARE/SPOT_ROUND yet, so OMNI is 3 instead of 5)
    constexpr int T5_LIGHT_NONE = 0;
    constexpr int T5_LIGHT_DIR = 1;
    constexpr int T5_LIGHT_SPOT = 2;
    constexpr int T5_LIGHT_OMNI = 3;

    vec3_t V3(const float* f)
    {
        return {f[0], f[1], f[2]};
    }

    vec3_t V3(const T5::vec3_t& v)
    {
        return {v.x, v.y, v.z};
    }

    void LhcToRhcCoordinates(float (&coords)[3])
    {
        const float two[3]{coords[0], coords[1], coords[2]};
        coords[0] = two[0];
        coords[1] = two[2];
        coords[2] = -two[1];
    }

    void LhcToRhcQuaternion(float (&quat)[4])
    {
        const float two[4]{quat[0], quat[1], quat[2], quat[3]};
        quat[0] = two[0];
        quat[1] = two[2];
        quat[2] = -two[1];
        quat[3] = two[3];
    }

    vec3_t moveVerticesToOrigin(std::vector<BSPVertex>& inout_vertBuffer)
    {
        if (inout_vertBuffer.empty())
            return {0.0f, 0.0f, 0.0f};

        vec3_t mins = inout_vertBuffer[0].pos;
        vec3_t maxs = inout_vertBuffer[0].pos;
        for (auto& vert : inout_vertBuffer)
            BSPUtil::updateAABBWithPoint(vert.pos, mins, maxs);

        vec3_t middle = BSPUtil::calcMiddleOfAABB(mins, maxs);
        for (auto& vert : inout_vertBuffer)
        {
            vert.pos.x -= middle.x;
            vert.pos.y -= middle.y;
            vert.pos.z -= middle.z;
        }
        return middle;
    }

    struct OutSurface
    {
        size_t surfaceStart;
        size_t surfaceCount;
    };

    struct PartitionData
    {
        size_t partitionIdx;
        size_t materialIdx;
    };

    class T5Unlinker
    {
    public:
        T5Unlinker(BSPData& dumpData, AssetDumpingContext& context)
            : m_data(dumpData),
              m_context(context)
        {
            const char* noXModels = getenv("OAT_T5BSP_NO_XMODELS");
            m_skipXModels = noXModels && *noXModels && *noXModels != '0';
        }

        // ---------------------------------------------------------------- collision

        void getPartitionsFromAABBTree(const T5::clipMap_t* clipmap, size_t aabbStartIndex, size_t aabbCount, std::vector<PartitionData>& partitionList)
        {
            std::deque<size_t> aabbQueue;
            for (size_t aabbIdx = 0; aabbIdx < aabbCount; aabbIdx++)
                aabbQueue.emplace_back(aabbStartIndex + aabbIdx);

            while (!aabbQueue.empty())
            {
                const size_t aabbIdx = aabbQueue.front();
                aabbQueue.pop_front();

                const T5::CollisionAabbTree* aabb = &clipmap->aabbTrees[aabbIdx];
                if (aabb->childCount == 0)
                    partitionList.emplace_back(PartitionData{static_cast<size_t>(aabb->u.partitionIndex), static_cast<size_t>(aabb->materialIndex)});
                else
                {
                    for (uint16_t childIdx = 0; childIdx < aabb->childCount; childIdx++)
                        aabbQueue.emplace_back(static_cast<size_t>(aabb->u.firstChildIndex) + childIdx);
                }
            }
        }

        void createSurfacesFromPartitions(const T5::clipMap_t* clipmap, std::vector<PartitionData>& partitionList, bool useWorldCoordinates, OutSurface& result)
        {
            // group partitions by material, keeping each partition once
            std::vector<std::pair<size_t, std::vector<size_t>>> materialPartitions;
            std::map<size_t, size_t> materialToGroup;
            std::unordered_set<uint64_t> seen;
            for (const auto& partitionData : partitionList)
            {
                const uint64_t key = (static_cast<uint64_t>(partitionData.materialIdx) << 32) | partitionData.partitionIdx;
                if (!seen.emplace(key).second)
                    continue;
                auto it = materialToGroup.find(partitionData.materialIdx);
                if (it == materialToGroup.end())
                {
                    materialToGroup[partitionData.materialIdx] = materialPartitions.size();
                    materialPartitions.emplace_back(partitionData.materialIdx, std::vector<size_t>{partitionData.partitionIdx});
                }
                else
                    materialPartitions[it->second].second.emplace_back(partitionData.partitionIdx);
            }

            result.surfaceCount = 0;
            result.surfaceStart = m_data.colWorld.surfaces.size();

            for (const auto& matPartition : materialPartitions)
            {
                // T5 partitions index triIndices as a flat uint16 array (3 per tri) into clipmap->verts
                std::vector<BSPVertex> outVertices;
                std::vector<size_t> outIndices;
                std::map<uint16_t, size_t> vertRemap;
                size_t triCount = 0;
                for (const auto partIdx : matPartition.second)
                {
                    const T5::CollisionPartition* partition = &clipmap->partitions[partIdx];
                    for (int k = 0; k < static_cast<unsigned char>(partition->triCount); k++)
                    {
                        const uint16_t* tri = &clipmap->triIndices[(static_cast<size_t>(partition->firstTri) + k) * 3];
                        size_t local[3];
                        for (int c = 0; c < 3; c++)
                        {
                            auto found = vertRemap.find(tri[c]);
                            if (found == vertRemap.end())
                            {
                                BSPVertex vert{};
                                vert.pos = V3(clipmap->verts[tri[c]]);
                                LhcToRhcCoordinates(vert.pos.v);
                                vert.color = whiteColour;
                                local[c] = outVertices.size();
                                vertRemap[tri[c]] = local[c];
                                outVertices.emplace_back(vert);
                            }
                            else
                                local[c] = found->second;
                        }
                        // reversed winding = LhcToRhcIndices
                        outIndices.emplace_back(local[2]);
                        outIndices.emplace_back(local[1]);
                        outIndices.emplace_back(local[0]);
                        triCount++;
                    }
                }
                if (outVertices.empty())
                    continue;

                // the BSP format uses uint16 indices; split very large terrain groups
                size_t triStart = 0;
                while (triStart < triCount)
                {
                    std::vector<BSPVertex> chunkVerts;
                    std::vector<uint16_t> chunkIdx;
                    std::map<size_t, uint16_t> chunkRemap;
                    size_t t = triStart;
                    for (; t < triCount; t++)
                    {
                        if (chunkVerts.size() + 3 > 0xFFFF)
                            break;
                        for (int c = 0; c < 3; c++)
                        {
                            const size_t src = outIndices[t * 3 + c];
                            auto f = chunkRemap.find(src);
                            if (f == chunkRemap.end())
                            {
                                chunkRemap[src] = static_cast<uint16_t>(chunkVerts.size());
                                chunkIdx.emplace_back(static_cast<uint16_t>(chunkVerts.size()));
                                chunkVerts.emplace_back(outVertices[src]);
                            }
                            else
                                chunkIdx.emplace_back(f->second);
                        }
                    }

                    BSPSurface outSurface{};
                    outSurface.isLocalCoords = !useWorldCoordinates;
                    outSurface.origin = {};
                    if (!useWorldCoordinates)
                        outSurface.origin = moveVerticesToOrigin(chunkVerts);
                    outSurface.materialIndex = matPartition.first;
                    outSurface.triCount = t - triStart;
                    outSurface.vertexCount = chunkVerts.size();
                    outSurface.indexOfFirstVertex = m_data.colWorld.vertices.size();
                    outSurface.indexOfFirstIndex = m_data.colWorld.indices.size();
                    m_data.colWorld.surfaces.emplace_back(outSurface);
                    m_data.colWorld.vertices.insert(m_data.colWorld.vertices.end(), chunkVerts.begin(), chunkVerts.end());
                    m_data.colWorld.indices.insert(m_data.colWorld.indices.end(), chunkIdx.begin(), chunkIdx.end());
                    result.surfaceCount++;
                    triStart = t;
                }
            }
        }

        void createSurfacesFromBrushes(const T5::clipMap_t* clipmap, std::vector<size_t>& brushList, bool useWorldCoordinates, OutSurface& result)
        {
            result.surfaceCount = 0;
            result.surfaceStart = m_data.colWorld.surfaces.size();
            std::unordered_set<size_t> uniqueBrushes;
            for (const size_t brushIdx : brushList)
            {
                if (!uniqueBrushes.emplace(brushIdx).second)
                    continue;

                const T5::cbrush_t* brush = &clipmap->brushes[brushIdx];

                std::vector<vec3_t> hullVerts;
                if (brush->numverts != 0)
                {
                    for (unsigned int vertIdx = 0; vertIdx < brush->numverts; vertIdx++)
                        hullVerts.emplace_back(V3(brush->verts[vertIdx]));
                }
                else
                {
                    // axial box brush
                    const vec3_t mins = V3(brush->mins);
                    const vec3_t maxs = V3(brush->maxs);
                    for (int i = 0; i < 8; i++)
                        hullVerts.push_back({(i & 1) ? maxs.x : mins.x, (i & 2) ? maxs.y : mins.y, (i & 4) ? maxs.z : mins.z});
                }

                if (hullVerts.size() < 4)
                {
                    con::debug("Brush {} with {} verts, skipping", brushIdx, hullVerts.size());
                    uniqueBrushes.erase(brushIdx);
                    continue;
                }

                for (auto& hv : hullVerts)
                    LhcToRhcCoordinates(hv.v);

                QuickHull<float> qh;
                auto hull = qh.getConvexHull(&hullVerts[0].x, hullVerts.size(), false, true);
                const std::vector<size_t> indexBuffer = hull.getIndexBuffer();
                const VertexDataSource<float> vertexBuffer = hull.getVertexBuffer();
                if (indexBuffer.empty())
                {
                    uniqueBrushes.erase(brushIdx);
                    continue;
                }

                std::vector<BSPVertex> outVertexBuffer;
                for (const auto& vertex : vertexBuffer)
                {
                    BSPVertex vert{};
                    vert.pos = {vertex.x, vertex.y, vertex.z};
                    vert.color = whiteColour;
                    outVertexBuffer.emplace_back(vert);
                }

                BSPSurface surface{};
                surface.isLocalCoords = !useWorldCoordinates;
                surface.origin = {};
                if (!useWorldCoordinates)
                    surface.origin = moveVerticesToOrigin(outVertexBuffer);
                surface.indexOfFirstVertex = m_data.colWorld.vertices.size();
                surface.indexOfFirstIndex = m_data.colWorld.indices.size();
                surface.triCount = indexBuffer.size() / 3;
                surface.vertexCount = outVertexBuffer.size();
                surface.materialIndex = colMaterialForFlags(clipmap, brush->axial_cflags[1][2], brush->axial_sflags[1][2]);
                m_data.colWorld.surfaces.emplace_back(surface);

                m_data.colWorld.vertices.insert(m_data.colWorld.vertices.end(), outVertexBuffer.begin(), outVertexBuffer.end());
                for (const auto index : indexBuffer)
                    m_data.colWorld.indices.emplace_back(static_cast<uint16_t>(index));
            }
            result.surfaceCount = m_data.colWorld.surfaces.size() - result.surfaceStart;
        }

        size_t colMaterialForFlags(const T5::clipMap_t* clipmap, int contentFlags, int surfaceFlags)
        {
            // brushes without per-side data pick their flags the same way a trace does
            for (unsigned i = 0; i < clipmap->numMaterials; i++)
            {
                if (clipmap->materials[i].contentFlags == contentFlags && clipmap->materials[i].surfaceFlags == surfaceFlags)
                    return i;
            }
            for (size_t i = clipmap->numMaterials; i < m_data.colWorld.materials.size(); i++)
            {
                const auto& mat = m_data.colWorld.materials[i];
                if (mat.contentFlags == contentFlags && mat.surfaceFlags == surfaceFlags && mat.materialName.starts_with("unknown_material_"))
                    return i;
            }

            BSPMaterial bspMaterial{};
            bspMaterial.materialName = std::format("unknown_material_{}", m_data.colWorld.materials.size());
            bspMaterial.materialType = MATERIAL_TYPE_TEXTURE;
            bspMaterial.materialColour = whiteColour;
            bspMaterial.surfaceFlags = surfaceFlags;
            bspMaterial.contentFlags = contentFlags;
            m_data.colWorld.materials.emplace_back(bspMaterial);
            return m_data.colWorld.materials.size() - 1;
        }

        void getBrushesFromLeafBrushNode(const T5::clipMap_t* clipmap, size_t leafBrushNodeIdx, std::vector<size_t>& brushList)
        {
            if (leafBrushNodeIdx == 0)
                return;

            std::deque<size_t> leafBrushNodeQueue;
            leafBrushNodeQueue.emplace_back(leafBrushNodeIdx);
            while (!leafBrushNodeQueue.empty())
            {
                const size_t lbnIdx = leafBrushNodeQueue.front();
                leafBrushNodeQueue.pop_front();
                const auto* leafBrushNode = &clipmap->leafbrushNodes[lbnIdx];

                if (leafBrushNode->leafBrushCount > 0)
                {
                    for (int16_t i = 0; i < leafBrushNode->leafBrushCount; i++)
                        brushList.emplace_back(static_cast<size_t>(leafBrushNode->data.leaf.brushes[i]));
                    continue;
                }

                if (leafBrushNode->leafBrushCount < 0)
                    leafBrushNodeQueue.emplace_back(lbnIdx + 1);
                leafBrushNodeQueue.emplace_back(lbnIdx + static_cast<size_t>(leafBrushNode->data.children.childOffset[0]));
                leafBrushNodeQueue.emplace_back(lbnIdx + static_cast<size_t>(leafBrushNode->data.children.childOffset[1]));
            }
        }

        void getStaticCollisionList(const T5::clipMap_t* clipmap, std::vector<PartitionData>& partitionList, std::vector<size_t>& brushList)
        {
            if (clipmap->numNodes == 0)
                return;

            std::deque<int16_t> nodeQueue;
            nodeQueue.emplace_back(0);
            while (!nodeQueue.empty())
            {
                const int16_t nodeIdx = nodeQueue.front();
                nodeQueue.pop_front();

                if (nodeIdx < 0)
                {
                    const int leafIndex = -1 - nodeIdx;
                    const T5::cLeaf_s* leaf = &clipmap->leafs[leafIndex];
                    if (leaf->collAabbCount != 0)
                        getPartitionsFromAABBTree(clipmap, leaf->firstCollAabbIndex, leaf->collAabbCount, partitionList);
                    if (leaf->leafBrushNode != 0)
                        getBrushesFromLeafBrushNode(clipmap, static_cast<size_t>(leaf->leafBrushNode), brushList);
                }
                else
                {
                    nodeQueue.emplace_back(clipmap->nodes[nodeIdx].children[0]);
                    nodeQueue.emplace_back(clipmap->nodes[nodeIdx].children[1]);
                }
            }
        }

        // ---------------------------------------------------------------- materials

        static const T5::GfxImage* imageOf(const T5::MaterialTextureDef& def)
        {
            return def.u.image;
        }

        static const T5::GfxImage* getMaterialColorMap(const T5::Material* material)
        {
            std::vector<const T5::MaterialTextureDef*> defs;
            for (auto i = 0u; i < material->textureCount; i++)
            {
                const auto* def = &material->textureTable[i];
                if (def->semantic == T5::TS_COLOR_MAP || (def->semantic >= T5::TS_COLOR0_MAP && def->semantic <= T5::TS_COLOR15_MAP))
                    defs.push_back(def);
            }
            if (defs.empty())
                return nullptr;
            for (const char* pattern : {"cp", "rk", "dp"})
            {
                for (const auto* def : defs)
                {
                    if (tolower(def->nameStart) == pattern[0] && tolower(def->nameEnd) == pattern[1])
                        return imageOf(*def);
                }
            }
            return imageOf(*defs[0]);
        }

        static const T5::GfxImage* getMaterialNormalMap(const T5::Material* material)
        {
            const T5::MaterialTextureDef* first = nullptr;
            for (auto i = 0u; i < material->textureCount; i++)
            {
                const auto* def = &material->textureTable[i];
                if (def->semantic != T5::TS_NORMAL_MAP)
                    continue;
                if (def->nameStart == 'n' && def->nameEnd == 'p')
                    return imageOf(*def);
                if (!first)
                    first = def;
            }
            return first ? imageOf(*first) : nullptr;
        }

        size_t createColMaterial(const T5::Material* material)
        {
            const char* matName = BSPUtil::trueAssetName(material->info.name);
            for (size_t matIdx = 0; matIdx < m_data.colWorld.materials.size(); matIdx++)
            {
                if (m_data.colWorld.materials[matIdx].materialName == matName)
                    return matIdx;
            }

            BSPMaterial bspMaterial{};
            bspMaterial.materialName = matName;
            bspMaterial.materialType = MATERIAL_TYPE_TEXTURE;
            bspMaterial.materialColour = whiteColour;
            m_data.colWorld.materials.emplace_back(bspMaterial);
            return m_data.colWorld.materials.size() - 1;
        }

        size_t createBspMaterial(const T5::Material* material, int surfFlags)
        {
            const char* matName = BSPUtil::trueAssetName(material->info.name);
            const int surfFlagsSimple = surfFlags & (SURF_CASTS_SUN_SHADOW | SURF_IS_SKY | SURF_NO_DRAW);
            for (size_t matIdx = 0; matIdx < m_data.gfxWorld.materials.size(); matIdx++)
            {
                const auto& mat = m_data.gfxWorld.materials[matIdx];
                if (mat.materialName == matName && mat.surfaceFlags == surfFlagsSimple)
                    return matIdx;
            }

            BSPMaterial bspMaterial{};
            bspMaterial.materialName = matName;
            bspMaterial.materialType = MATERIAL_TYPE_TEXTURE;
            bspMaterial.materialColour = whiteColour;
            bspMaterial.surfaceFlags = surfFlagsSimple;
            bspMaterial.contentFlags = surfFlagsSimple;
            if (const auto* colorMap = getMaterialColorMap(material))
                bspMaterial.imageName = BSPUtil::trueAssetName(colorMap->name);
            if (const auto* normalMap = getMaterialNormalMap(material))
                bspMaterial.normalName = BSPUtil::trueAssetName(normalMap->name);

            m_data.gfxWorld.materials.emplace_back(bspMaterial);
            return m_data.gfxWorld.materials.size() - 1;
        }

        // T5 GfxSurface::flags -> T6 GfxSurfaceFlags (the low bits are shared; the material name settles sky/nodraw)
        static int convertSurfaceFlags(const T5::GfxSurface& surface)
        {
            int flags = surface.flags & SURF_CASTS_SUN_SHADOW;
            const char* name = surface.material ? BSPUtil::trueAssetName(surface.material->info.name) : "";
            const char* techset = surface.material && surface.material->techniqueSet ? surface.material->techniqueSet->name : "";
            if ((surface.flags & SURF_IS_SKY) || strstr(techset, "sky") || strstr(name, "sky"))
                flags |= SURF_IS_SKY;
            if (surface.flags & SURF_NO_DRAW)
                flags |= SURF_NO_DRAW;
            return flags;
        }

        // ---------------------------------------------------------------- xmodels

        std::map<std::string, std::pair<size_t, size_t>> m_xmodelToSurfGfx;
        std::map<std::string, std::pair<size_t, size_t>> m_xmodelToSurfCol;

        void addXmodelSurfaces(const T5::XModel* xmodel, bool isGfx)
        {
            BSPWorld* world = isGfx ? &m_data.gfxWorld : &m_data.colWorld;
            if (xmodel->numLods == 0)
                return;

            const uint16_t lodIdx = static_cast<uint16_t>(xmodel->numLods - 1);
            for (auto surfaceIndex = 0u; surfaceIndex < xmodel->lodInfo[lodIdx].numsurfs; surfaceIndex++)
            {
                const size_t realSurfIndex = surfaceIndex + xmodel->lodInfo[lodIdx].surfIndex;
                const auto& surface = xmodel->surfs[realSurfIndex];
                if (!surface.verts0 || !surface.triIndices)
                    continue;

                BSPSurface outSurface{};
                outSurface.materialIndex = isGfx ? createBspMaterial(xmodel->materialHandles[realSurfIndex], 0) : createColMaterial(xmodel->materialHandles[realSurfIndex]);
                outSurface.triCount = surface.triCount;
                outSurface.vertexCount = surface.vertCount;
                outSurface.indexOfFirstVertex = world->vertices.size();
                outSurface.indexOfFirstIndex = world->indices.size();
                world->surfaces.emplace_back(outSurface);

                for (auto vertIndex = 0u; vertIndex < surface.vertCount; vertIndex++)
                {
                    const auto* vertex = &surface.verts0[vertIndex];
                    BSPVertex outVertex{};
                    outVertex.pos = V3(vertex->xyz);
                    LhcToRhcCoordinates(outVertex.pos.v);
                    T5::Common::Vec3UnpackUnitVec(vertex->normal, outVertex.normal.v);
                    LhcToRhcCoordinates(outVertex.normal.v);
                    T5::Common::Vec2UnpackTexCoords(vertex->texCoord, outVertex.texCoord.v);
                    outVertex.color = whiteColour;
                    world->vertices.emplace_back(outVertex);
                }

                for (auto triIndex = 0u; triIndex < surface.triCount; triIndex++)
                {
                    const auto& tri = surface.triIndices[triIndex];
                    world->indices.emplace_back(tri.i[2]);
                    world->indices.emplace_back(tri.i[1]);
                    world->indices.emplace_back(tri.i[0]);
                }
            }
        }

        const T5::XModel* findXModel(const std::string& name)
        {
            const auto* asset = m_context.m_zone.m_pools.GetAsset<T5::AssetXModel>(name);
            if (asset != nullptr && !asset->IsReference())
                return asset->Asset();

            for (const auto& zone : m_context.m_loaded_zones)
            {
                const auto* asset2 = zone->GetZone().m_pools.GetAsset<T5::AssetXModel>(name);
                if (asset2 != nullptr && !asset2->IsReference())
                    return asset2->Asset();
            }

            con::warn("Unable to find non-reference xmodel {}", name);
            return nullptr;
        }

        void surfacesForXModel(const std::string& name, bool isGfx, size_t& outStart, size_t& outCount)
        {
            auto& cache = isGfx ? m_xmodelToSurfGfx : m_xmodelToSurfCol;
            BSPWorld& world = isGfx ? m_data.gfxWorld : m_data.colWorld;
            if (const auto it = cache.find(name); it != cache.end())
            {
                outStart = it->second.first;
                outCount = it->second.second;
                return;
            }
            outStart = world.surfaces.size();
            if (const auto* xmodel = findXModel(name))
                addXmodelSurfaces(xmodel, isGfx);
            outCount = world.surfaces.size() - outStart;
            cache[name] = {outStart, outCount};
        }

        // ---------------------------------------------------------------- clipmap

        void dumpClipmapXModels(const T5::clipMap_t* clipmap)
        {
            if (m_skipXModels)
                return;
            for (size_t modelIdx = 0; modelIdx < clipmap->numStaticModels; modelIdx++)
            {
                const T5::cStaticModel_s* colModel = &clipmap->staticModelList[modelIdx];
                if (!colModel->xmodel)
                    continue;

                vec3_t invAxis[3]{V3(colModel->invScaledAxis[0]), V3(colModel->invScaledAxis[1]), V3(colModel->invScaledAxis[2])};
                vec3_t outOrig[3]{};
                BSPUtil::matrixTranspose3x3(invAxis, outOrig);

                // invScaledAxis = axis / scale, so each row's length is 1/scale
                vec3_t origAxis[3]{};
                float scale[3];
                for (int i = 0; i < 3; i++)
                {
                    const float length = sqrtf(outOrig[i].x * outOrig[i].x + outOrig[i].y * outOrig[i].y + outOrig[i].z * outOrig[i].z);
                    scale[i] = length > 0.0f ? 1.0f / length : 1.0f;
                    origAxis[i] = {outOrig[i].x * scale[i], outOrig[i].y * scale[i], outOrig[i].z * scale[i]};
                }

                BSPXModel model{};
                model.name = BSPUtil::trueAssetName(colModel->xmodel->name);
                model.origin = V3(colModel->origin);
                LhcToRhcCoordinates(model.origin.v);
                model.rotationQuaternion = BSPUtil::convertAxisToQuat(origAxis);
                LhcToRhcQuaternion(model.rotationQuaternion.v);
                model.scale = {scale[0], scale[1], scale[2]};
                surfacesForXModel(model.name, false, model.surfaceStart, model.surfaceCount);
                m_data.colWorld.xmodels.emplace_back(model);
            }
        }

        void dumpClipmapRopes(const T5::clipMap_t* clipMap)
        {
            for (int ropeIdx = 0; ropeIdx < clipMap->num_constraints; ropeIdx++)
            {
                const T5::PhysConstraint* constraint = &clipMap->constraints[ropeIdx];
                if (constraint->type != T5::CONSTRAINT_ROPE)
                    continue;
                if (constraint->attach_point_type1 != T5::ATTACH_POINT_WORLD || constraint->attach_point_type2 != T5::ATTACH_POINT_WORLD)
                    continue;

                BSPRope rope{};
                if (constraint->material)
                    rope.material = BSPUtil::trueAssetName(constraint->material->info.name);
                rope.startPoint = V3(constraint->pos);
                LhcToRhcCoordinates(rope.startPoint.v);
                rope.endPoint = V3(constraint->pos2);
                LhcToRhcCoordinates(rope.endPoint.v);
                rope.length = constraint->distance;
                rope.width = constraint->minAngle;
                rope.scale = constraint->scale.x == 0.0f ? 1.0f : constraint->scale.x;
                m_data.ropes.emplace_back(rope);
            }
        }

        void dumpClipmap(const T5::clipMap_t* clipmap)
        {
            for (unsigned int i = 0; i < clipmap->numMaterials; i++)
            {
                const auto* colMaterial = &clipmap->materials[i];
                BSPMaterial bspMaterial{};
                bspMaterial.materialName = BSPUtil::trueAssetName(colMaterial->material);
                bspMaterial.materialType = MATERIAL_TYPE_TEXTURE;
                bspMaterial.materialColour = whiteColour;
                bspMaterial.surfaceFlags = colMaterial->surfaceFlags;
                bspMaterial.contentFlags = colMaterial->contentFlags;
                m_data.colWorld.materials.emplace_back(bspMaterial);
            }

            dumpClipmapXModels(clipmap);
            dumpClipmapRopes(clipmap);
            if (clipmap->originalDynEntCount != 0)
                con::warn("Skipping {} dynamic (physics) entities: not converted yet", clipmap->originalDynEntCount);

            std::vector<PartitionData> partitionList;
            std::vector<size_t> brushList;
            getStaticCollisionList(clipmap, partitionList, brushList);

            OutSurface result{};
            createSurfacesFromPartitions(clipmap, partitionList, true, result);
            m_data.staticTerrainSurfaceCount = result.surfaceCount;
            m_data.staticTerrainSurfaceStart = result.surfaceStart;

            createSurfacesFromBrushes(clipmap, brushList, false, result);
            m_data.staticBrushSurfaceCount = result.surfaceCount;
            m_data.staticBrushSurfaceStart = result.surfaceStart;

            con::info("Collision: {} terrain surfaces from {} partitions, {} brushes", m_data.staticTerrainSurfaceCount, partitionList.size(), m_data.staticBrushSurfaceCount);
        }

        size_t createModelFromIndex(size_t modelIndex, const T5::GfxWorld* gfxworld, const T5::clipMap_t* clipmap)
        {
            BSPModel model{};

            const auto& gfxModel = gfxworld->models[modelIndex];
            if (gfxModel.surfaceCount != 0)
            {
                model.surfaceSide = MSS_GFX;
                model.gfxSurfaceCount = gfxModel.surfaceCount;
                // script surfaces follow the static ones, in the same order
                size_t updatedSurfIndex = static_cast<size_t>(gfxModel.startSurfIndex) - gfxworld->dpvs.staticSurfaceCount;
                updatedSurfIndex += m_data.staticSurfaceStart + m_data.staticSurfaceCount;
                model.gfxSurfaceIndex = updatedSurfIndex;
            }

            const T5::cLeaf_s* leaf = &clipmap->cmodels[modelIndex].leaf;
            if (leaf->collAabbCount != 0)
            {
                model.surfaceSide = gfxModel.surfaceCount != 0 ? MSS_BOTH : MSS_COL;
                model.surfaceType = MST_TERRAIN;
                std::vector<PartitionData> partitionList;
                getPartitionsFromAABBTree(clipmap, leaf->firstCollAabbIndex, leaf->collAabbCount, partitionList);
                OutSurface result{};
                createSurfacesFromPartitions(clipmap, partitionList, true, result);
                model.colTerrainSurfaceCount = result.surfaceCount;
                model.colTerrainSurfaceIndex = result.surfaceStart;
            }
            if (leaf->leafBrushNode != 0)
            {
                model.surfaceSide = gfxModel.surfaceCount != 0 ? MSS_BOTH : MSS_COL;
                model.surfaceType = leaf->collAabbCount != 0 ? MST_BOTH : MST_BRUSH;
                std::vector<size_t> brushList;
                getBrushesFromLeafBrushNode(clipmap, static_cast<size_t>(leaf->leafBrushNode), brushList);
                OutSurface result{};
                createSurfacesFromBrushes(clipmap, brushList, true, result);
                model.colBrushSurfaceCount = result.surfaceCount;
                model.colBrushSurfaceIndex = result.surfaceStart;
            }

            m_data.models.emplace_back(model);
            return m_data.models.size() - 1;
        }

        // ---------------------------------------------------------------- map ents

        static bspEntityType entityTypeForClass(const std::string& classname)
        {
            if (classname.starts_with("weapon_"))
                return ET_WEAPON;
            if (classname == "info_notnull" || classname == "info_notnull_big" || classname == "script_origin")
                return ET_POINT;
            if (classname == "info_volume")
                return ET_VOLUME;
            if (classname.starts_with("trigger_"))
                return ET_TRIGGER;
            if (classname == "light")
                return ET_LIGHT;
            if (classname == "script_brushmodel")
                return ET_BRUSHMODEL;
            if (classname == "script_model")
                return ET_MODEL;
            if (classname == "script_struct")
                return ET_STRUCT;
            if (classname == "script_vehicle" || classname == "info_vehicle_node" || classname == "info_vehicle_node_rotate")
                return ET_VEHICLE;
            if (classname.starts_with("zbarrier_"))
                return ET_ZBARRIER;
            if (classname.starts_with("node_"))
                return ET_PATHNODE;
            if (classname.starts_with("actor_"))
                return ET_ACTOR;
            if (classname == "glass")
                return ET_GLASS;
            if (classname == "rope")
                return ET_ROPE;
            return ET_OTHER;
        }

        void dumpMapEnts(const T5::MapEnts* mapEnts, const T5::GfxWorld* gfxworld, const T5::clipMap_t* clipmap)
        {
            // OAT_T5BSP_ENTS: a rewritten entity file (BO1 gameplay entities converted to BO2 conventions) replaces the map's own
            std::string entityString(mapEnts->entityString, mapEnts->numEntityChars > 0 ? strnlen(mapEnts->entityString, mapEnts->numEntityChars) : strlen(mapEnts->entityString));
            const char* entsOverride = getenv("OAT_T5BSP_ENTS");
            const bool hasOverride = entsOverride && *entsOverride;
            if (hasOverride)
            {
                std::ifstream file(entsOverride, std::ios::binary);
                if (file)
                {
                    entityString.assign(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
                    con::info("Using entity override {}", entsOverride);
                }
                else
                    con::error("Could not read entity override {}", entsOverride);
            }
            size_t pos = 0;
            size_t entIdx = 1;
            std::map<size_t, size_t> brushModelCache;
            std::map<std::string, size_t> droppedEntities;

            auto readQuoted = [&](std::string& out) -> bool
            {
                const auto start = entityString.find('"', pos);
                if (start == std::string::npos)
                    return false;
                const auto end = entityString.find('"', start + 1);
                if (end == std::string::npos)
                    return false;
                out = entityString.substr(start + 1, end - start - 1);
                pos = end + 1;
                return true;
            };

            while (true)
            {
                const auto open = entityString.find('{', pos);
                if (open == std::string::npos)
                    break;
                pos = open + 1;

                BSPEntity entity{};
                entity.rotationQuaternion = {0.0f, 0.0f, 0.0f, 1.0f};
                entity.type = ET_OTHER;
                entity.hasModel = false;
                entity.classname = "unknown";
                entity.uniqueEntityNumber = entIdx++;

                while (true)
                {
                    const auto nextQuote = entityString.find('"', pos);
                    const auto close = entityString.find('}', pos);
                    if (close == std::string::npos || (nextQuote != std::string::npos && close < nextQuote) || nextQuote == std::string::npos)
                    {
                        pos = close == std::string::npos ? entityString.size() : close + 1;
                        break;
                    }

                    std::string key, value;
                    if (!readQuoted(key) || !readQuoted(value))
                        break;

                    if (key == "classname")
                    {
                        entity.classname = value;
                        entity.type = entityTypeForClass(value);
                    }

                    if (key == "origin")
                    {
                        entity.origin = BSPUtil::convertStringToVec3(value.c_str());
                        LhcToRhcCoordinates(entity.origin.v);
                    }
                    else if (key == "angles")
                    {
                        vec3_t angles = BSPUtil::convertStringToVec3(value.c_str());
                        entity.rotationQuaternion = BSPUtil::convertAnglesToQuat(angles);
                        LhcToRhcQuaternion(entity.rotationQuaternion.v);
                    }
                    else if (key == "model")
                    {
                        if (!value.empty() && value[0] == '*')
                        {
                            const auto modelIdx = static_cast<size_t>(atol(value.c_str() + 1));
                            if (modelIdx == 0 || modelIdx >= static_cast<size_t>(gfxworld->modelCount) || modelIdx >= clipmap->numSubModels)
                            {
                                con::warn("Entity {} references invalid brush model {}", entity.uniqueEntityNumber, value);
                                continue;
                            }
                            entity.hasModel = true;
                            if (const auto it = brushModelCache.find(modelIdx); it != brushModelCache.end())
                                entity.modelIndex = it->second;
                            else
                                entity.modelIndex = brushModelCache[modelIdx] = createModelFromIndex(modelIdx, gfxworld, clipmap);
                        }
                        else
                        {
                            const std::string xmodelName = BSPUtil::trueAssetName(value.c_str());
                            surfacesForXModel(xmodelName, false, entity.surfaceStart, entity.surfaceCount);
                            entity.entries.emplace_back(BSPEntityEntry{key, xmodelName});
                        }
                    }
                    else
                        entity.entries.emplace_back(BSPEntityEntry{key, value});
                }

                // path nodes need matching gameworld path data (not converted yet) and BO1 actor spawners
                // have no BO2 equivalent; the BO2 scripts crash on nodes the gameworld doesn't know
                if (entity.type == ET_PATHNODE || (entity.type == ET_ACTOR && !hasOverride))
                {
                    droppedEntities[entity.type == ET_PATHNODE ? "path nodes" : "actor spawners"]++;
                    continue;
                }
                m_data.entities.emplace_back(std::move(entity));
            }
            for (const auto& [kind, count] : droppedEntities)
                con::info("Dropped {} {} (not converted yet)", count, kind);

            addMissingT6Entities();
            con::info("Map ents: {} entities, {} brush models", m_data.entities.size(), m_data.models.size());
        }

        // BO2 maps need an intermission camera; BO1 SP-based zombie maps have none, so place one above the player start
        void addMissingT6Entities()
        {
            const BSPEntity* start = nullptr;
            for (const auto& entity : m_data.entities)
            {
                if (entity.classname == "mp_global_intermission")
                    return;
                if (!start && entity.classname == "info_player_start")
                    start = &entity;
            }

            BSPEntity intermission{};
            intermission.uniqueEntityNumber = m_data.entities.size() + 1;
            intermission.type = ET_OTHER;
            intermission.classname = "mp_global_intermission";
            intermission.entries.emplace_back(BSPEntityEntry{"classname", intermission.classname});
            intermission.rotationQuaternion = start ? start->rotationQuaternion : vec4_t{0.0f, 0.0f, 0.0f, 1.0f};
            intermission.origin = start ? start->origin : vec3_t{0.0f, 0.0f, 0.0f};
            intermission.origin.y += 64.0f; // glTF space: y is up
            m_data.entities.emplace_back(intermission);
        }

        // ---------------------------------------------------------------- gfx world

        void addSurfaceGroups(const T5::GfxWorld* gfxWorld, std::vector<std::pair<size_t, std::vector<size_t>>>& materialMap)
        {
            for (const auto& matSurf : materialMap)
            {
                // merge the surfaces of one material; T5 surfaces index into large shared vertex windows,
                // so only the vertices a surface actually uses are copied (split when uint16 indices run out)
                std::vector<BSPVertex> verts;
                std::vector<uint16_t> indices;
                std::unordered_map<size_t, uint16_t> remap;
                size_t triCount = 0;

                auto flush = [&]()
                {
                    if (verts.empty())
                        return;
                    BSPSurface outSurface{};
                    outSurface.materialIndex = matSurf.first;
                    outSurface.triCount = triCount;
                    outSurface.vertexCount = verts.size();
                    outSurface.indexOfFirstVertex = m_data.gfxWorld.vertices.size();
                    outSurface.indexOfFirstIndex = m_data.gfxWorld.indices.size();
                    m_data.gfxWorld.surfaces.emplace_back(outSurface);
                    m_data.gfxWorld.vertices.insert(m_data.gfxWorld.vertices.end(), verts.begin(), verts.end());
                    m_data.gfxWorld.indices.insert(m_data.gfxWorld.indices.end(), indices.begin(), indices.end());
                    verts.clear();
                    indices.clear();
                    remap.clear();
                    triCount = 0;
                };

                auto vertexFor = [&](size_t globalIndex) -> uint16_t
                {
                    if (const auto it = remap.find(globalIndex); it != remap.end())
                        return it->second;
                    const T5::GfxWorldVertex& in = gfxWorld->draw.vd.vertices[globalIndex];
                    BSPVertex out{};
                    out.pos = V3(in.xyz);
                    LhcToRhcCoordinates(out.pos.v);
                    T5::Common::Vec3UnpackUnitVec(in.normal, out.normal.v);
                    LhcToRhcCoordinates(out.normal.v);
                    out.texCoord = {in.texCoord[0], in.texCoord[1]};
                    out.color = whiteColour;
                    const auto local = static_cast<uint16_t>(verts.size());
                    verts.emplace_back(out);
                    remap.emplace(globalIndex, local);
                    return local;
                };

                if (!gfxWorld->draw.vd.vertices || !gfxWorld->draw.indices)
                {
                    T5BSP_TRACE("  world has no vertex/index data");
                    return;
                }

                for (const auto surfIdx : matSurf.second)
                {
                    const T5::GfxSurface* surface = &gfxWorld->dpvs.surfaces[surfIdx];
                    const auto& tris = surface->tris;
                    if (tris.triCount == 0 || tris.vertexCount == 0)
                        continue;
                    if (static_cast<size_t>(tris.firstVertex) + tris.vertexCount > gfxWorld->draw.vertexCount
                        || static_cast<size_t>(tris.baseIndex) + tris.triCount * 3u > static_cast<size_t>(gfxWorld->draw.indexCount))
                    {
                        if (m_badSurfaces++ < 5)
                            con::warn("Surface {} is out of range, skipped", surfIdx);
                        continue;
                    }

                    const uint16_t* triIndices = &gfxWorld->draw.indices[tris.baseIndex];
                    for (uint16_t t = 0; t < tris.triCount; t++)
                    {
                        if (verts.size() + 3 > 0xFFFF)
                            flush();
                        uint16_t local[3];
                        for (int c = 0; c < 3; c++)
                            local[c] = vertexFor(static_cast<size_t>(tris.firstVertex) + triIndices[t * 3 + c]);
                        // reversed winding = LhcToRhcIndices
                        indices.emplace_back(local[2]);
                        indices.emplace_back(local[1]);
                        indices.emplace_back(local[0]);
                        triCount++;
                    }
                }
                flush();
            }
        }

        void collectSurfacesWithSameMaterials(const T5::GfxWorld* gfxWorld, size_t surfStart, size_t surfEnd, std::vector<std::pair<size_t, std::vector<size_t>>>& out_materialMap)
        {
            std::map<size_t, size_t> groupForMaterial;
            for (size_t surfIdx = surfStart; surfIdx < surfEnd; surfIdx++)
            {
                const T5::GfxSurface* surface = &gfxWorld->dpvs.surfaces[surfIdx];
                if (!surface->material || isToolMaterial(surface->material))
                    continue;
                const size_t materialIndex = createBspMaterial(surface->material, convertSurfaceFlags(*surface));
                if (const auto it = groupForMaterial.find(materialIndex); it != groupForMaterial.end())
                    out_materialMap[it->second].second.emplace_back(surfIdx);
                else
                {
                    groupForMaterial[materialIndex] = out_materialMap.size();
                    out_materialMap.emplace_back(materialIndex, std::vector<size_t>{surfIdx});
                }
            }
        }

        static bool isToolMaterial(const T5::Material* material)
        {
            const char* techset = material->techniqueSet ? material->techniqueSet->name : "";
            return strncmp(techset, "wc_tools", 8) == 0;
        }

        static bool isTransparent(const T5::Material* material)
        {
            // T5 sort keys: opaque world/model surfaces sort before the blended/decal ones
            return material && material->info.sortKey >= 6;
        }

        void dumpGfxWorldSurfaces(const T5::GfxWorld* gfxWorld)
        {
            std::vector<std::pair<size_t, std::vector<size_t>>> litOpaque, litTrans, emissiveOpaque, emissiveTrans;

            // T5 groups: lit (opaque), decal (blended on top of lit), emissive (unlit: sky, glows)
            const auto& dpvs = gfxWorld->dpvs;
            collectSurfacesWithSameMaterials(gfxWorld, dpvs.litSurfsBegin, dpvs.litSurfsEnd, litOpaque);
            collectSurfacesWithSameMaterials(gfxWorld, dpvs.decalSurfsBegin, dpvs.decalSurfsEnd, litTrans);
            std::vector<std::pair<size_t, std::vector<size_t>>> emissiveAll;
            collectSurfacesWithSameMaterials(gfxWorld, dpvs.emissiveSurfsBegin, dpvs.emissiveSurfsEnd, emissiveAll);
            // static surfaces outside the three ranges (sky, water, ...) are drawn unlit
            const unsigned rangesEnd = std::max({dpvs.litSurfsEnd, dpvs.decalSurfsEnd, dpvs.emissiveSurfsEnd});
            if (rangesEnd < dpvs.staticSurfaceCount)
            {
                std::map<std::string, size_t> techsets;
                for (unsigned i = rangesEnd; i < dpvs.staticSurfaceCount; i++)
                {
                    const auto* material = gfxWorld->dpvs.surfaces[i].material;
                    techsets[material && material->techniqueSet ? material->techniqueSet->name : "?"]++;
                }
                std::string summary;
                for (const auto& [name, count] : techsets)
                    summary += std::format(" {}x{}", name, count);
                con::info("{} static surfaces outside lit/decal/emissive, added as emissive:{}", dpvs.staticSurfaceCount - rangesEnd, summary);
                collectSurfacesWithSameMaterials(gfxWorld, rangesEnd, dpvs.staticSurfaceCount, emissiveAll);
            }
            for (auto& group : emissiveAll)
            {
                const auto* material = gfxWorld->dpvs.surfaces[group.second.front()].material;
                (isTransparent(material) ? emissiveTrans : emissiveOpaque).emplace_back(std::move(group));
            }

            m_data.staticSurfaceStart = 0;

            m_data.litOpaqueSurfaceStart = m_data.gfxWorld.surfaces.size();
            addSurfaceGroups(gfxWorld, litOpaque);
            m_data.litOpaqueSurfaceCount = m_data.gfxWorld.surfaces.size() - m_data.litOpaqueSurfaceStart;

            m_data.litTransparentSurfaceStart = m_data.gfxWorld.surfaces.size();
            addSurfaceGroups(gfxWorld, litTrans);
            m_data.litTransparentSurfaceCount = m_data.gfxWorld.surfaces.size() - m_data.litTransparentSurfaceStart;

            m_data.emissiveOpaqueSurfaceStart = m_data.gfxWorld.surfaces.size();
            addSurfaceGroups(gfxWorld, emissiveOpaque);
            m_data.emissiveOpaqueSurfaceCount = m_data.gfxWorld.surfaces.size() - m_data.emissiveOpaqueSurfaceStart;

            m_data.emissiveTransparentSurfaceStart = m_data.gfxWorld.surfaces.size();
            addSurfaceGroups(gfxWorld, emissiveTrans);
            m_data.emissiveTransparentSurfaceCount = m_data.gfxWorld.surfaces.size() - m_data.emissiveTransparentSurfaceStart;

            m_data.staticSurfaceCount = m_data.gfxWorld.surfaces.size();

            // script (brush model) surfaces stay unmerged and in order, entities index them
            for (int surfIdx = static_cast<int>(dpvs.staticSurfaceCount); surfIdx < gfxWorld->surfaceCount; surfIdx++)
            {
                const T5::GfxSurface* surface = &gfxWorld->dpvs.surfaces[surfIdx];
                const size_t materialIndex = surface->material ? createBspMaterial(surface->material, convertSurfaceFlags(*surface)) : 0;
                std::vector<std::pair<size_t, std::vector<size_t>>> single;
                if (surface->material)
                    single.emplace_back(materialIndex, std::vector<size_t>{static_cast<size_t>(surfIdx)});
                const size_t before = m_data.gfxWorld.surfaces.size();
                addSurfaceGroups(gfxWorld, single);
                if (m_data.gfxWorld.surfaces.size() == before)
                {
                    // keep one (empty) surface so the brush model surface indices stay aligned
                    BSPSurface empty{};
                    empty.materialIndex = materialIndex;
                    empty.indexOfFirstVertex = m_data.gfxWorld.vertices.size();
                    empty.indexOfFirstIndex = m_data.gfxWorld.indices.size();
                    m_data.gfxWorld.surfaces.emplace_back(empty);
                }
            }

            con::info("World: {} T5 surfaces -> {} static ({} lit, {} decal, {} emissive) + {} script surfaces",
                      gfxWorld->surfaceCount,
                      m_data.staticSurfaceCount,
                      m_data.litOpaqueSurfaceCount,
                      m_data.litTransparentSurfaceCount,
                      m_data.emissiveOpaqueSurfaceCount + m_data.emissiveTransparentSurfaceCount,
                      m_data.gfxWorld.surfaces.size() - m_data.staticSurfaceCount);
        }

        void dumpGfxWorldXModels(const T5::GfxWorld* gfxWorld)
        {
            if (m_skipXModels)
            {
                con::info("Static models skipped (OAT_T5BSP_NO_XMODELS)");
                return;
            }
            for (size_t modelIdx = 0; modelIdx < gfxWorld->dpvs.smodelCount; modelIdx++)
            {
                const auto* gfxModel = &gfxWorld->dpvs.smodelDrawInsts[modelIdx];
                if (!gfxModel->model)
                    continue;

                BSPXModel model{};
                model.name = BSPUtil::trueAssetName(gfxModel->model->name);
                model.origin = V3(gfxModel->placement.origin);
                LhcToRhcCoordinates(model.origin.v);
                vec3_t axis[3]{V3(gfxModel->placement.axis[0]), V3(gfxModel->placement.axis[1]), V3(gfxModel->placement.axis[2])};
                model.rotationQuaternion = BSPUtil::convertAxisToQuat(axis);
                LhcToRhcQuaternion(model.rotationQuaternion.v);
                model.scale = {gfxModel->placement.scale, gfxModel->placement.scale, gfxModel->placement.scale};
                model.doesCastShadow = true;
                surfacesForXModel(model.name, true, model.surfaceStart, model.surfaceCount);
                m_data.gfxWorld.xmodels.emplace_back(model);
            }
            con::info("Static models: {}", m_data.gfxWorld.xmodels.size());
        }

        void dumpGfxWorldSun(const T5::GfxWorld* gfxWorld)
        {
            const auto& sun = gfxWorld->sunParse.sunSettings[0];
            m_data.sunlight = {};
            m_data.sunlight.type = LIGHT_TYPE_DIRECTIONAL;
            m_data.sunlight.colour = {sun.sunDiffuseColor[0], sun.sunDiffuseColor[1], sun.sunDiffuseColor[2]};
            m_data.sunlight.intensity = sun.sunDiffuseColor[3] > 0.0f ? sun.sunDiffuseColor[3] : 1.0f;
            vec3_t angles = V3(sun.angles);
            m_data.sunlight.forwardVector = BSPUtil::convertAnglesToForward(angles);
            LhcToRhcCoordinates(m_data.sunlight.forwardVector.v);
            m_data.sunlight.rollAngle = 0.0f;
            m_data.hasSunlightBeenSet = true;
        }

        void dumpGfxWorldRProbes(const T5::GfxWorld* gfxWorld)
        {
            for (size_t probeIdx = 0; probeIdx < gfxWorld->draw.reflectionProbeCount; probeIdx++)
            {
                const auto* probe = &gfxWorld->draw.reflectionProbes[probeIdx];
                if (!probe->reflectionImage)
                    continue;
                BSPRPRobe outProbe{};
                outProbe.origin = V3(probe->origin);
                LhcToRhcCoordinates(outProbe.origin.v);
                outProbe.image = BSPUtil::trueAssetName(probe->reflectionImage->name);
                m_data.rProbes.emplace_back(outProbe);
            }
        }

        void dumpGfxWorld(const T5::GfxWorld* gfxWorld)
        {
            if (gfxWorld->skyBoxModel)
                m_data.skyboxName = gfxWorld->skyBoxModel;
            T5BSP_TRACE("sun");
            dumpGfxWorldSun(gfxWorld);
            T5BSP_TRACE("surfaces %d static %u lit %u-%u decal %u-%u emissive %u-%u verts %u", gfxWorld->surfaceCount, gfxWorld->dpvs.staticSurfaceCount,
                        gfxWorld->dpvs.litSurfsBegin, gfxWorld->dpvs.litSurfsEnd, gfxWorld->dpvs.decalSurfsBegin, gfxWorld->dpvs.decalSurfsEnd,
                        gfxWorld->dpvs.emissiveSurfsBegin, gfxWorld->dpvs.emissiveSurfsEnd, gfxWorld->draw.vertexCount);
            dumpGfxWorldSurfaces(gfxWorld);
            T5BSP_TRACE("xmodels");
            dumpGfxWorldXModels(gfxWorld);
            T5BSP_TRACE("probes");
            dumpGfxWorldRProbes(gfxWorld);
        }

        // ---------------------------------------------------------------- com world

        void dumpComWorld(const T5::ComWorld* comWorld, const std::vector<const T5::GfxLightDef*>& lightDefs)
        {
            std::map<int, size_t> typeCounts;
            for (unsigned int lightIdx = 0; lightIdx < comWorld->primaryLightCount; lightIdx++)
            {
                const T5::ComPrimaryLight* inLight = &comWorld->primaryLights[lightIdx];
                typeCounts[inLight->type]++;
                if (lightIdx < BSP_DEFAULT_LIGHT_COUNT)
                    continue; // empty light and sun, the sun comes from the gfx world

                BSPLight outLight{};
                switch (inLight->type)
                {
                case T5_LIGHT_DIR:
                    outLight.type = LIGHT_TYPE_DIRECTIONAL;
                    break;
                case T5_LIGHT_SPOT:
                    outLight.type = LIGHT_TYPE_SPOT;
                    outLight.innerConeAngle = acosf(std::clamp(inLight->cosHalfFovInner, -1.0f, 1.0f));
                    outLight.outerConeAngle = acosf(std::clamp(inLight->cosHalfFovOuter, -1.0f, 1.0f));
                    break;
                case T5_LIGHT_OMNI:
                    outLight.type = LIGHT_TYPE_POINT;
                    break;
                default:
                    continue;
                }

                outLight.forwardVector = V3(inLight->dir);
                LhcToRhcCoordinates(outLight.forwardVector.v);
                outLight.rollAngle = inLight->angle[2];
                outLight.colour = {inLight->color[0], inLight->color[1], inLight->color[2]};
                outLight.pos = V3(inLight->origin);
                LhcToRhcCoordinates(outLight.pos.v);
                outLight.range = inLight->radius;
                outLight.intensity = 1.0f;
                // T5 aAbB is not limited to the 0..1 range T6 expects; fall back to the T6 round default then
                outLight.superEllipse = {inLight->aAbB[0], inLight->aAbB[1], inLight->aAbB[2], inLight->aAbB[3]};
                if (std::ranges::any_of(inLight->aAbB, [](float v) { return v < 0.0f || v > 1.0f; }))
                    outLight.superEllipse = {0.75f, 1.0f, 0.75f, 1.0f};
                outLight.cullDistance = inLight->cullDist > 0 ? static_cast<size_t>(inLight->cullDist) : 1000;
                outLight.roundness = 1.0f;

                if (inLight->defName)
                {
                    for (const auto* lightDef : lightDefs)
                    {
                        if (lightDef->name && !strcmp(inLight->defName, lightDef->name) && lightDef->attenuation.image)
                        {
                            outLight.image = BSPUtil::trueAssetName(lightDef->attenuation.image->name);
                            break;
                        }
                    }
                }

                m_data.lights.emplace_back(outLight);
            }

            std::string summary;
            for (const auto& [type, count] : typeCounts)
                summary += std::format(" type{}={}", type, count);
            con::info("Primary lights: {} ({} converted):{}", comWorld->primaryLightCount, m_data.lights.size(), summary);
        }

    private:
        size_t m_badSurfaces = 0;
        bool m_skipXModels = false;

        BSPData& m_data;
        AssetDumpingContext& m_context;
    };
} // namespace

void T5::BSP::dumpBSPDataT5(BSPData& dumpData, const std::string& zoneName, const BSPAssetPtrsT5& assetPtrs, AssetDumpingContext& context)
{
    dumpData.name = zoneName;
    dumpData.isZombiesMap = true;

    T5Unlinker unlinker(dumpData, context);
    T5BSP_TRACE("comworld");
    unlinker.dumpComWorld(assetPtrs.comworld, assetPtrs.lightDefs);
    T5BSP_TRACE("gfxworld");
    unlinker.dumpGfxWorld(assetPtrs.gfxworld);
    T5BSP_TRACE("clipmap");
    unlinker.dumpClipmap(assetPtrs.clipmap);
    T5BSP_TRACE("mapents");
    unlinker.dumpMapEnts(assetPtrs.mapEnts, assetPtrs.gfxworld, assetPtrs.clipmap);
    T5BSP_TRACE("done");
}
