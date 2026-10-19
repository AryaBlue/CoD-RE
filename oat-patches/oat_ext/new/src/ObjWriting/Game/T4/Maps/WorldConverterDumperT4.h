#pragma once

#include "Dumping/AbstractAssetDumper.h"
#include "Game/T4/T4.h"

namespace world_converter
{
    class LightDefDumperT4 final : public AbstractAssetDumper<T4::AssetLightDef>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::GfxLightDef>& asset) override;
    };
    class ComWorldDumperT4 final : public AbstractAssetDumper<T4::AssetComWorld>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::ComWorld>& asset) override;
    };
    class GfxWorldDumperT4 final : public AbstractAssetDumper<T4::AssetGfxWorld>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::GfxWorld>& asset) override;
    };

    // T4 custom maps store their usable collision asset in the PVS slot.  The
    // non-PVS slot is exposed as "clipmap_unused" by OAT and is normally empty.
    class ClipMapDumperT4 final : public AbstractAssetDumper<T4::AssetClipMapPvs>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::clipMap_t>& asset) override;
    };
    // Path nodes of the SP gameworld (WaW zombie maps are SP maps) as JSON
    class PathDataDumperT4 final : public AbstractAssetDumper<T4::AssetGameWorldSp>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::GameWorldSp>& asset) override;
    };
} // namespace world_converter
