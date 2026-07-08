import type { Ref } from 'vue';
import { type SettingValue, useSetting } from '@/modules/settings/use-setting';

export interface AssetMovementSettings {
  assetMovementAmountTolerance: Readonly<Ref<SettingValue<'assetMovementAmountTolerance'>>>;
  assetMovementTimeRange: Readonly<Ref<SettingValue<'assetMovementTimeRange'>>>;
}

/**
 * Domain facade bundling the two asset-movement matching settings that are always read together (the
 * amount tolerance and the time range). Reads through `useSetting`, so consumers import no store.
 */
export function useAssetMovementSettings(): AssetMovementSettings {
  return {
    assetMovementAmountTolerance: useSetting('assetMovementAmountTolerance'),
    assetMovementTimeRange: useSetting('assetMovementTimeRange'),
  };
}
