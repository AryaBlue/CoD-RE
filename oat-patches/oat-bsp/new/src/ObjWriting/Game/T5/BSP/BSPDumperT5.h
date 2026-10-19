#pragma once

#include "Dumping/AbstractAssetDumper.h"
#include "Game/T5/T5.h"

namespace T5
{
    namespace BSP
    {
        // Dumps a Black Ops (T5) map as bsp/map_gfx.glb + bsp/map_col.glb, the input format of the T6 BSP linker.
        class DumperT5 final : public IAssetDumper
        {
        public:
            [[nodiscard]] std::optional<asset_type_t> GetHandlingAssetType() const override;
            [[nodiscard]] size_t GetProgressTotalCount(AssetDumpingContext& context) const override;
            void Dump(AssetDumpingContext& context) override;
        };
    } // namespace BSP
} // namespace T5
