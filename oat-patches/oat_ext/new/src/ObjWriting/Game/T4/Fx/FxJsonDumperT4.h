#pragma once

#include "Dumping/AbstractAssetDumper.h"
#include "Game/T4/T4.h"

namespace fx
{
    // waw2bo2: lossless dump of a compiled T4 FxEffectDef (fx/<name>.w2bfx.json).
    // Every field of the runtime struct is written as is (samples, ranges, raw
    // flags); referenced assets are written by name. The converter translates it.
    class JsonDumperT4 final : public AbstractAssetDumper<T4::AssetFx>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::FxEffectDef>& asset) override;
    };
} // namespace fx
