import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/modules/assets/types';

/** Which of the two ignore actions the current handling rules out. */
interface DisabledIgnoreActions {
  ignore: boolean;
  unIgnore: boolean;
}

interface UseManagedAssetActionsOptions {
  /** How ignored assets are currently being treated. */
  ignoredHandling: MaybeRefOrGetter<IgnoredAssetsHandlingType>;
  /**
   * Called when the ignored list has to be re-read.
   *
   * @remarks
   * Showing only ignored assets makes the list itself the table's contents, so it has to be fresh
   * before the table renders from it.
   */
  onIgnoredStale: () => void;
  /** The selected asset identifiers, which this clears. */
  selected: Ref<string[]>;
}

interface UseManagedAssetActionsReturn {
  /** Empties the selection. */
  clearSelection: () => void;
  /**
   * Which ignore actions are unavailable.
   *
   * @remarks
   * Ignoring is pointless while only ignored assets are shown, and un-ignoring is pointless while
   * they are excluded, because in each case the row would leave the table it was acted on from.
   */
  disabledIgnoreActions: ComputedRef<DisabledIgnoreActions>;
}

/**
 * The bulk actions above the managed assets table: what the current ignore handling allows, and
 * clearing the selection.
 *
 * @returns the disabled state of the ignore buttons and the selection reset
 */
export function useManagedAssetActions(
  options: UseManagedAssetActionsOptions,
): UseManagedAssetActionsReturn {
  const { ignoredHandling, onIgnoredStale, selected } = options;

  const disabledIgnoreActions = computed<DisabledIgnoreActions>(() => ({
    ignore: toValue(ignoredHandling) === IgnoredAssetHandlingType.SHOW_ONLY,
    unIgnore: toValue(ignoredHandling) === IgnoredAssetHandlingType.EXCLUDE,
  }));

  function clearSelection(): void {
    set(selected, []);
  }

  function refreshIgnoredWhenShownAlone(handling: IgnoredAssetsHandlingType): void {
    if (handling === IgnoredAssetHandlingType.SHOW_ONLY)
      onIgnoredStale();
  }

  watch(() => toValue(ignoredHandling), refreshIgnoredWhenShownAlone);

  return {
    clearSelection,
    disabledIgnoreActions,
  };
}
