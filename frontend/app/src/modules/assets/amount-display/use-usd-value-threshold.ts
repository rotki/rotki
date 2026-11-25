import type { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef } from 'vue';
import { useSetting } from '@/modules/settings/use-setting';

export function useValueThreshold(balanceSource: BalanceSource): ComputedRef<string | undefined> {
  const balanceValueThreshold = useSetting('balanceValueThreshold');

  return computed<string | undefined>(() => get(balanceValueThreshold)[balanceSource]);
}
