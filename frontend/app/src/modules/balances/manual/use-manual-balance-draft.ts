import type { ManualBalance, RawManualBalance } from '@/modules/balances/types/manual-balances';
import { Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { set } from '@vueuse/shared';
import { type MaybeRefOrGetter, nextTick, type Ref, ref, toValue } from 'vue';
import { BalanceType } from '@/modules/balances/types/balances';
import { TRADE_LOCATION_EXTERNAL } from '@/modules/core/common/defaults';
import { useAddQuery } from '@/modules/core/common/use-add-query';

interface UseManualBalanceDraftReturn {
  /** The balance the dialog edits; unset while the dialog is closed. */
  modelBalance: Ref<ManualBalance | RawManualBalance | undefined>;
  /** Opens the dialog on a blank balance of the tab's type. */
  add: () => void;
  /** Opens the dialog when the route carries `?add=`, and clears the query either way. */
  consumeAddQuery: () => Promise<boolean>;
}

/**
 * The manual balance the page's dialog creates or edits, seeded for the tab in view.
 *
 * @param tab - the page's tab; `liabilities` seeds a liability, anything else an asset
 */
export function useManualBalanceDraft(tab: MaybeRefOrGetter<string>): UseManualBalanceDraftReturn {
  const modelBalance = ref<ManualBalance | RawManualBalance>();

  function add(): void {
    set(modelBalance, {
      amount: Zero,
      asset: '',
      balanceType: toValue(tab) === 'liabilities' ? BalanceType.LIABILITY : BalanceType.ASSET,
      label: '',
      location: TRADE_LOCATION_EXTERNAL,
      tags: null,
    } satisfies RawManualBalance);
  }

  const { consumeAddQuery } = useAddQuery(() => {
    startPromise(nextTick(() => add()));
  });

  return { add, consumeAddQuery, modelBalance };
}
