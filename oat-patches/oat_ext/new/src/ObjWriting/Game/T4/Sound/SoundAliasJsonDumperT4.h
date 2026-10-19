#pragma once
#include "Dumping/AbstractAssetDumper.h"
#include "Game/T4/T4.h"

namespace sound
{
    class DriverGlobalsJsonDumperT4 final : public AbstractAssetDumper<T4::AssetSoundDriverGlobals>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::SndDriverGlobals>& asset) override;
    };
    class AliasJsonDumperT4 final : public AbstractAssetDumper<T4::AssetSound>
    {
    protected:
        void DumpAsset(AssetDumpingContext& context, const XAssetInfo<T4::snd_alias_list_t>& asset) override;
    };
}
