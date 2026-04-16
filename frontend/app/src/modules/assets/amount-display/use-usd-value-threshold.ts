import type { ComputedRef } from 'vue';
import type { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

export function useValueThreshold(balanceSource: BalanceSource): ComputedRef<string | undefined> {
  const { balanceValueThreshold } = storeToRefs(useFrontendSettingsStore());

  return computed<string | undefined>(() => get(balanceValueThreshold)[balanceSource]);
}
