import type { ComputedRef, Ref } from 'vue';
import type { LocationLabel } from '@/modules/core/common/location';
import { startPromise } from '@shared/utils';
import { hasAccountAddress } from '@/modules/accounts/account-helpers';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useHistoryStore } from '@/modules/history/use-history-store';

interface UseDivergenceSelectionReturn {
  modelSelectedAsset: Ref<string | undefined>;
  modelSelectedChain: Ref<string | undefined>;
  modelSelectedLocationLabel: Ref<string>;
  chainOptions: ComputedRef<string[]>;
  locationLabelOptions: ComputedRef<LocationLabel[]>;
  selectedEvmChain: ComputedRef<string | undefined>;
}

/**
 * Owns the chain/location-label/asset selection for the balance divergence panel: it builds the
 * list of tracked EVM location labels, keeps the selects defaulted to valid options, and fetches
 * the label list on mount. The `model*` refs are writable so the selects can bind them via v-model.
 */
export function useDivergenceSelection(): UseDivergenceSelectionReturn {
  const { getEvmChainName, isEvm, matchChain } = useSupportedChains();
  const { fetchLocationLabels } = useHistoryDataFetching();
  const { locationLabels } = storeToRefs(useHistoryStore());
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

  const modelSelectedAsset = shallowRef<string>();
  const modelSelectedChain = shallowRef<string>();
  const modelSelectedLocationLabel = shallowRef<string>('');

  const availableLocationLabels = computed<LocationLabel[]>(() => {
    const labels = new Map<string, LocationLabel>();

    const addLabel = (item: LocationLabel): void => {
      const chain = matchChain(item.location);
      if (!chain || !isEvm(chain) || !getEvmChainName(chain))
        return;

      labels.set(`${chain}:${item.locationLabel.toLowerCase()}`, {
        location: chain,
        locationLabel: item.locationLabel,
      });
    };

    get(locationLabels).forEach(addLabel);
    Object.values(get(accountsPerChain))
      .flatMap(accounts => accounts)
      .filter(hasAccountAddress)
      .forEach(account => addLabel({
        location: account.chain,
        locationLabel: getAccountAddress(account),
      }));

    return [...labels.values()];
  });

  const chainOptions = computed<string[]>(() => {
    const options = new Set<string>();
    for (const item of get(availableLocationLabels)) {
      const chain = matchChain(item.location);
      if (chain)
        options.add(chain);
    }
    return [...options].sort((a, b) => a.localeCompare(b));
  });

  const locationLabelOptions = computed<LocationLabel[]>(() => {
    const chain = get(modelSelectedChain);
    if (!chain)
      return [];

    return get(availableLocationLabels)
      .filter(item => matchChain(item.location) === chain)
      .sort((a, b) => a.locationLabel.localeCompare(b.locationLabel));
  });

  const selectedEvmChain = computed<string | undefined>(() => {
    const chain = get(modelSelectedChain);
    return chain ? getEvmChainName(chain) : undefined;
  });

  watch(chainOptions, (options) => {
    const current = get(modelSelectedChain);
    if (!current || !options.includes(current))
      set(modelSelectedChain, options[0]);
  }, { immediate: true });

  watch(locationLabelOptions, (options) => {
    const current = get(modelSelectedLocationLabel);
    if (!current || !options.some(option => option.locationLabel === current))
      set(modelSelectedLocationLabel, options[0]?.locationLabel ?? '');
  }, { immediate: true });

  // The asset dropdown is scoped to the selected chain, so a token picked for one chain (e.g. an
  // Arbitrum asset) is invalid after switching chains. Clear it to avoid submitting a mismatch the
  // backend rejects ("<asset> is not on <chain>").
  watch(modelSelectedChain, () => {
    set(modelSelectedAsset, undefined);
  });

  onMounted(() => {
    startPromise(fetchLocationLabels());
  });

  return {
    chainOptions,
    locationLabelOptions,
    modelSelectedAsset,
    modelSelectedChain,
    modelSelectedLocationLabel,
    selectedEvmChain,
  };
}
