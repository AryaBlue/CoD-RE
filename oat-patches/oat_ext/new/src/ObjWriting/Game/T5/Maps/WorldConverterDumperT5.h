#pragma once

#include "Dumping/AbstractAssetDumper.h"
#include "Game/T5/T5.h"

// Black Ops (T5) world dumps in the waw2bo2 interchange formats (see Game/T4/Maps/WorldConverterDumperT4), so the
// WaW -> BO2 converter can stage BO1 maps. BO1 keeps the same data as WaW with a few layout changes: render buffers
// live in GfxWorld::draw, brush sides carry content/surface flags instead of a clip material index, and the sun is
// described by GfxWorldSunColor settings.
namespace world_converter
{
    class LightDefDumperT5 final : public AbstractAssetDumper<T5::AssetLightDef>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T5::GfxLightDef>& asset) override;
    };

    class ComWorldDumperT5 final : public AbstractAssetDumper<T5::AssetComWorld>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T5::ComWorld>& asset) override;
    };

    class GfxWorldDumperT5 final : public AbstractAssetDumper<T5::AssetGfxWorld>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T5::GfxWorld>& asset) override;
    };

    // BO1 zones use either clipmap slot depending on how the map was linked
    class ClipMapDumperT5 final : public AbstractAssetDumper<T5::AssetClipMap>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T5::clipMap_t>& asset) override;
    };

    class ClipMapPvsDumperT5 final : public AbstractAssetDumper<T5::AssetClipMapPvs>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T5::clipMap_t>& asset) override;
    };

    // BO1 zombie maps are SP maps
    class PathDataDumperT5 final : public AbstractAssetDumper<T5::AssetGameWorldSp>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T5::GameWorldSp>& asset) override;
    };
} // namespace world_converter
