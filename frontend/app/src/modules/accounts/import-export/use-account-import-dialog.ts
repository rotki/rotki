import type { Ref } from 'vue';

interface UseAccountImportDialogReturn {
  /** Bound with `v-model` by the one mounted dialog, so it is writable on purpose. */
  modelOpen: Ref<boolean>;
  show: () => void;
}

/**
 * Whether the account CSV import dialog is open.
 *
 * @remarks
 * Shared, so the add account dialog can open the import dialog that the page's menu mounts. Users
 * look for an import where they add accounts, not only in the page menu.
 */
export const useAccountImportDialog = createSharedComposable((): UseAccountImportDialogReturn => {
  const modelOpen = ref<boolean>(false);

  function show(): void {
    set(modelOpen, true);
  }

  return { modelOpen, show };
});
