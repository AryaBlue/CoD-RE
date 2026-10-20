#include "BSPDumperT5.h"

#include "BSPUnlinkerT5.h"
#include "Game/T6/BSP/BSPWriter.h"

#include <cstdio>

using namespace T5;
using namespace T5::BSP;

std::optional<asset_type_t> DumperT5::GetHandlingAssetType() const
{
    return std::nullopt;
}

size_t DumperT5::GetProgressTotalCount(AssetDumpingContext& context) const
{
    return 0;
}

void DumperT5::Dump(AssetDumpingContext& context)
{
    const auto& gfxWorldPool = context.m_zone.m_pools.PoolAssets<AssetGfxWorld>();
    const auto& colWorldPool = context.m_zone.m_pools.PoolAssets<AssetClipMap>();
    const auto& colWorldPvsPool = context.m_zone.m_pools.PoolAssets<AssetClipMapPvs>();
    const auto& mapEntsPool = context.m_zone.m_pools.PoolAssets<AssetMapEnts>();
    const auto& comWorldPool = context.m_zone.m_pools.PoolAssets<AssetComWorld>();
    if (gfxWorldPool.size() != 1 || mapEntsPool.size() != 1 || comWorldPool.size() != 1 || colWorldPool.size() + colWorldPvsPool.size() != 1)
        return;

    fputs("[t5bsp] dumper start\n", stderr);
    con::info("BSP (T5) dumping started");

    BSPAssetPtrsT5 assetPtrs{};
    assetPtrs.gfxworld = (*gfxWorldPool.begin())->Asset();
    assetPtrs.mapEnts = (*mapEntsPool.begin())->Asset();
    assetPtrs.comworld = (*comWorldPool.begin())->Asset();
    assetPtrs.clipmap = colWorldPool.size() == 1 ? (*colWorldPool.begin())->Asset() : (*colWorldPvsPool.begin())->Asset();
    for (const auto* lightDef : context.m_zone.m_pools.PoolAssets<AssetLightDef>())
        assetPtrs.lightDefs.emplace_back(lightDef->Asset());

    T6::BSP::BSPData dumpData;
    dumpBSPDataT5(dumpData, context.m_zone.m_name, assetPtrs, context);

    con::info("BSP (T5) writing started");

    const auto gfxAssetFile = context.OpenAssetFile("bsp/map_gfx.glb");
    const auto colAssetFile = context.OpenAssetFile("bsp/map_col.glb");
    if (!gfxAssetFile || !colAssetFile)
    {
        con::error("Unable to open bsp/map_gfx.glb or bsp/map_col.glb for writing.");
        return;
    }

    T6::BSP::writeDumpDataToGltf(dumpData, gfxAssetFile, colAssetFile);

    con::info("Dumped BSP \"{}\"", context.m_zone.m_name);
}
