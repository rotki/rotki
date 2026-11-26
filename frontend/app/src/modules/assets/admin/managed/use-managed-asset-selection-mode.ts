import { get, set } from '@vueuse/shared';
import { computed, type Ref, shallowRef, type WritableComputedRef } from 'vue';

interface UseManagedAssetSelectionModeReturn {
  /** Whether the table shows its checkbox column; toggled from the toolbar. */
  modelSelectionMode: Ref<boolean>;
  /**
   * The table's selection model.
   *
   * @remarks
   * `undefined` outside selection mode, which is what makes the table drop its checkbox column.
   * Writing `undefined` clears the selection.
   */
  tableSelection: WritableComputedRef<string[] | undefined>;
}

export function useManagedAssetSelectionMode(selected: Ref<string[]>): UseManagedAssetSelectionModeReturn {
  const modelSelectionMode = shallowRef<boolean>(false);

  const tableSelection = computed<string[] | undefined>({
    get: () => (get(modelSelectionMode) ? get(selected) : undefined),
    set: (value?: string[]) => set(selected, value ?? []),
  });

  return {
    modelSelectionMode,
    tableSelection,
  };
}
