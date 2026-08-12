import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { type Filters, tokenKindOf } from '@/modules/assets/detection/use-newly-detected-filter';
import { useNewlyDetectedTokens } from '@/modules/assets/detection/use-newly-detected-tokens';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { arrayify } from '@/modules/core/common/data/array';
import { uniqueStrings } from '@/modules/core/common/data/data';

interface UseNewlyDetectedSelectionOptions {
  /** What the bar has narrowed the table to, which is what "select all" has to agree with. */
  filters: MaybeRefOrGetter<Filters>;
  /** How many rows the current filter found. */
  found: MaybeRefOrGetter<number>;
  /** Re-reads the table after rows are accepted or marked as spam. */
  refetch: () => Promise<void>;
}

interface UseNewlyDetectedSelectionReturn {
  /** Bound with `v-model` by the table, so it stays writable. */
  modelSelected: Ref<string[]>;
  allSelected: ComputedRef<boolean>;
  toggleSelection: () => Promise<void>;
  removeTokens: (identifiers?: string | string[]) => Promise<void>;
  markAsSpam: (identifiers?: string | string[]) => Promise<void>;
}

/**
 * Which newly detected tokens are picked, and the two things that can be done to them.
 *
 * Selecting everything means everything the table is *showing*, so it asks for the identifiers of
 * the kind the pill narrowed to rather than of every kind. For the same reason a narrowing clears
 * the selection: it was made against rows that are no longer on screen.
 */
export function useNewlyDetectedSelection(
  options: UseNewlyDetectedSelectionOptions,
): UseNewlyDetectedSelectionReturn {
  const { filters, found, refetch } = options;

  const { getAllIdentifiers, removeNewDetectedTokens } = useNewlyDetectedTokens();
  const { markAssetsAsSpam } = useSpamAsset();

  const modelSelected = ref<string[]>([]);

  const tokenKind = computed(() => tokenKindOf(toValue(filters)));

  const allSelected = computed<boolean>(() => {
    const selectionLength = get(modelSelected).length;
    return selectionLength > 0 && toValue(found) === selectionLength;
  });

  function getIdentifiers(identifiers?: string | string[]): string[] {
    return identifiers ? arrayify(identifiers) : get(modelSelected);
  }

  async function toggleSelection(): Promise<void> {
    const selectedLength = get(modelSelected).length;
    const allIdentifiers = await getAllIdentifiers(get(tokenKind));

    set(modelSelected, selectedLength === allIdentifiers.length ? [] : allIdentifiers);
  }

  async function removeTokens(identifiers?: string | string[]): Promise<void> {
    await removeNewDetectedTokens(getIdentifiers(identifiers));
    set(modelSelected, []);
    await refetch();
  }

  async function markAsSpam(identifiers?: string | string[]): Promise<void> {
    const ids = getIdentifiers(identifiers).filter(uniqueStrings);
    const status = await markAssetsAsSpam(ids);

    if (status.success)
      await removeTokens(ids);
  }

  watch(tokenKind, () => {
    set(modelSelected, []);
  });

  return {
    allSelected,
    markAsSpam,
    modelSelected,
    removeTokens,
    toggleSelection,
  };
}
