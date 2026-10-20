#pragma once

#include "Dumping/AbstractAssetDumper.h"
#include "Game/T6/T6.h"

namespace world_converter
{
    // waw2bo2 world interchange (W2BSP001 .gfx.bin), the same format the T4 fork writes.
    // waw2bo2/world.py read_gfx_world is the reader; write_world_fbx turns it into BSP/map_gfx.fbx.
    class GfxWorldDumperT6 final : public AbstractAssetDumper<T6::AssetGfxWorld>
    {
    public:
        explicit GfxWorldDumperT6(const AssetPool<T6::AssetGfxWorld::Type>& pool);

    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T6::AssetGfxWorld::Type>& asset) override;
    };

    // W2BSP001 .clip.bin (read_collision). T6 keeps clipmap and clipmap_pvs in one pool.
    class ClipMapDumperT6 final : public AbstractAssetDumper<T6::AssetClipMap>
    {
    public:
        explicit ClipMapDumperT6(const AssetPool<T6::AssetClipMap::Type>& pool);

    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T6::AssetClipMap::Type>& asset) override;
    };
} // namespace world_converter
