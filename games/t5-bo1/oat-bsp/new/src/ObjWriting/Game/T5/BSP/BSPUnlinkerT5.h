#pragma once

#include "BSP/BSP.h"
#include "Dumping/AssetDumpingContext.h"
#include "Game/T5/T5.h"

#include <string>
#include <vector>

namespace T5
{
    namespace BSP
    {
        struct BSPAssetPtrsT5
        {
            const T5::MapEnts* mapEnts;
            const T5::ComWorld* comworld;
            const T5::GfxWorld* gfxworld;
            const T5::clipMap_t* clipmap;
            std::vector<const T5::GfxLightDef*> lightDefs;
        };

        // Converts a Black Ops (T5) map's world assets into the game-neutral BSPData used by the T6 BSP linker.
        void dumpBSPDataT5(T6::BSP::BSPData& dumpData, const std::string& zoneName, const BSPAssetPtrsT5& assetPtrs, AssetDumpingContext& context);
    } // namespace BSP
} // namespace T5
