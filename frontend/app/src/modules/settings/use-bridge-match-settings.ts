import type { Ref } from 'vue';
import { type SettingValue, useSetting } from '@/modules/settings/use-setting';

export interface BridgeMatchSettings {
  bridgeMatchAmountTolerance: Readonly<Ref<SettingValue<'bridgeMatchAmountTolerance'>>>;
  bridgeMatchTimeRange: Readonly<Ref<SettingValue<'bridgeMatchTimeRange'>>>;
}

/**
 * Domain facade bundling the two bridge matching settings that are always read together (the
 * amount tolerance and the time range). These are separate from the asset movement pair because
 * bridge relayer fees need a looser tolerance, and the backend auto-matcher uses these values, so
 * the manual search has to default to the same window it did.
 */
export function useBridgeMatchSettings(): BridgeMatchSettings {
  return {
    bridgeMatchAmountTolerance: useSetting('bridgeMatchAmountTolerance'),
    bridgeMatchTimeRange: useSetting('bridgeMatchTimeRange'),
  };
}
