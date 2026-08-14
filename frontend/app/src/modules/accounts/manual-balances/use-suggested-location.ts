import type { MaybeRefOrGetter } from 'vue';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useLocationStore } from '@/modules/core/common/use-location-store';

interface SuggestedLocationOptions {
  /** An existing balance already has the location it was saved with, so nothing is suggested. */
  readonly editing: MaybeRefOrGetter<boolean>;
  readonly apply: (location: string) => void;
}

interface SuggestedLocationReturn {
  /** Call when the user picks a location, after which none is suggested again. */
  readonly markChosen: () => void;
}

/**
 * Fills the location in from the chain the chosen asset lives on, for as long as the user has not
 * picked one themselves. The chain is named with underscores where the location uses spaces.
 */
export function useSuggestedLocation(
  asset: MaybeRefOrGetter<string>,
  options: SuggestedLocationOptions,
): SuggestedLocationReturn {
  const { apply, editing } = options;

  const { getAssetInfo } = useAssetInfoRetrieval();
  const { tradeLocations } = storeToRefs(useLocationStore());

  const chosen = shallowRef<boolean>(false);

  watch(() => toValue(asset), (asset) => {
    if (!asset || toValue(editing) || get(chosen))
      return;

    const evmChain = getAssetInfo(asset)?.evmChain;
    if (!evmChain)
      return;

    const location = get(tradeLocations).find(item => item.identifier === evmChain.split('_').join(' '));
    if (location)
      apply(location.identifier);
  });

  return {
    markChosen: (): void => {
      set(chosen, true);
    },
  };
}
