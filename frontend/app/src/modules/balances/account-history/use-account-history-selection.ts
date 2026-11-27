import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type WritableComputedRef } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  AccountHistoryQueryKeys,
  type AccountHistoryRange,
  type AccountHistorySelection,
  parseSelection,
  toSelectionQuery,
} from '@/modules/balances/account-history/account-history-selection';

interface UseAccountHistorySelectionReturn {
  selection: ComputedRef<AccountHistorySelection>;
  modelAccount: WritableComputedRef<string | undefined>;
  modelAsset: WritableComputedRef<string | undefined>;
  modelLocation: WritableComputedRef<string | undefined>;
  modelRange: WritableComputedRef<AccountHistoryRange>;
}

const OWN_KEYS: ReadonlySet<string> = new Set<string>(Object.values(AccountHistoryQueryKeys));

/**
 * The account history page's selection, read from and written to the route query.
 *
 * @remarks
 * Picking another account clears the asset and location, and picking another asset clears the
 * location: what was picked below belonged to the previous choice and may not exist for the new
 * one. A picker writing back the value it already holds changes nothing, so it cannot clear the
 * picks below it. Query keys the page does not own are left alone.
 */
export function useAccountHistorySelection(): UseAccountHistorySelectionReturn {
  const route = useRoute();
  const router = useRouter();

  const selection = computed<AccountHistorySelection>(() => parseSelection(route.query));

  function update(changes: Partial<AccountHistorySelection>): void {
    const foreign = Object.fromEntries(Object.entries(route.query).filter(([key]) => !OWN_KEYS.has(key)));
    const query = { ...foreign, ...toSelectionQuery({ ...get(selection), ...changes }) };
    startPromise(router.replace({ query }));
  }

  const modelAccount = computed<string | undefined>({
    get: () => get(selection).account,
    set: (account) => {
      if (account !== get(selection).account)
        update({ account, asset: undefined, location: undefined });
    },
  });

  const modelAsset = computed<string | undefined>({
    get: () => get(selection).asset,
    set: (asset) => {
      if (asset !== get(selection).asset)
        update({ asset, location: undefined });
    },
  });

  const modelLocation = computed<string | undefined>({
    get: () => get(selection).location,
    set: (location) => {
      if (location !== get(selection).location)
        update({ location });
    },
  });

  const modelRange = computed<AccountHistoryRange>({
    get: () => get(selection).range,
    set: (range) => {
      if (range !== get(selection).range)
        update({ range });
    },
  });

  return { modelAccount, modelAsset, modelLocation, modelRange, selection };
}
