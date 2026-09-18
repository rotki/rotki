import type { Ref } from 'vue';

interface UseMissingPricesDialogReturn {
  /** Bound with `v-model` by the one mounted dialog, so it is writable on purpose. */
  modelOpen: Ref<boolean>;
  show: () => void;
}

/**
 * Whether the missing prices dialog is open.
 *
 * @remarks
 * Shared, so an action center row on any page can open the one dialog mounted beside the center.
 */
export const useMissingPricesDialog = createSharedComposable((): UseMissingPricesDialogReturn => {
  const modelOpen = ref<boolean>(false);

  function show(): void {
    set(modelOpen, true);
  }

  return { modelOpen, show };
});
