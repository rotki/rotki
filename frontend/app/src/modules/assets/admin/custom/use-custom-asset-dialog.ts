import type { Nullable } from '@rotki/common';
import type { MaybeRefOrGetter, Ref } from 'vue';
import type { CustomAsset } from '@/modules/assets/types';

interface UseCustomAssetDialogOptions {
  /** The assets currently on the page, searched when the route names one to edit. */
  assets: MaybeRefOrGetter<CustomAsset[]>;
  /** An asset the route names, which opens straight into its edit dialog. */
  identifier: MaybeRefOrGetter<Nullable<string>>;
}

interface UseCustomAssetDialogReturn {
  /** Opens the dialog on a blank asset. */
  add: () => void;
  /**
   * Consumes an `?add=` query, opening the dialog on a blank asset.
   *
   * @remarks
   * The query is cleared afterwards, so a reload does not reopen the dialog.
   */
  consumeAddQuery: () => Promise<void>;
  /** Opens the dialog on an existing asset. */
  edit: (asset: CustomAsset) => void;
  /**
   * Opens the dialog on the asset with this identifier.
   *
   * @remarks
   * Only assets on the current page can be found, so this does nothing for one the table has not
   * loaded; an unknown identifier is ignored rather than opening a blank dialog.
   */
  editAsset: (assetId: Nullable<string>) => void;
  /** The asset the dialog is editing; `null` while adding. */
  modelEditableItem: Ref<CustomAsset | null>;
  /** Whether the add/edit dialog is open. */
  modelOpenDialog: Ref<boolean>;
}

/**
 * Owns which custom asset the add/edit dialog is showing, and the three ways it gets opened: a
 * button, a row, and the route.
 *
 * @returns the dialog's state and the ways to open it
 */
export function useCustomAssetDialog(options: UseCustomAssetDialogOptions): UseCustomAssetDialogReturn {
  const { assets, identifier } = options;

  const router = useRouter();
  const route = useRoute();

  const modelEditableItem = shallowRef<CustomAsset | null>(null);
  const modelOpenDialog = shallowRef<boolean>(false);

  function add(): void {
    set(modelEditableItem, null);
    set(modelOpenDialog, true);
  }

  function edit(asset: CustomAsset): void {
    set(modelEditableItem, asset);
    set(modelOpenDialog, true);
  }

  function editAsset(assetId: Nullable<string>): void {
    if (!assetId)
      return;

    const asset = toValue(assets).find(({ identifier: id }) => id === assetId);
    if (asset)
      edit(asset);
  }

  async function consumeAddQuery(): Promise<void> {
    if (!get(route).query.add)
      return;

    add();
    await router.replace({ query: {} });
  }

  watch(() => toValue(identifier), (assetId) => {
    editAsset(assetId);
  });

  return {
    add,
    consumeAddQuery,
    edit,
    editAsset,
    modelEditableItem,
    modelOpenDialog,
  };
}
