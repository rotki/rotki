import type { Nullable, SupportedAsset } from '@rotki/common';
import type { MaybeRefOrGetter, Ref } from 'vue';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { EVM_TOKEN } from '@/modules/assets/types';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';

function emptyAsset(): SupportedAsset {
  return {
    active: true,
    address: '',
    assetType: EVM_TOKEN,
    customAssetType: '',
    decimals: null,
    ended: null,
    forked: null,
    identifier: '',
    isRebasing: false,
    protocol: '',
    underlyingTokens: null,
  };
}

interface UseManagedAssetFormReturn {
  /** Asset types the form offers; empty when the backend could not be reached. */
  assetTypes: Readonly<Ref<string[]>>;
  /** Opens the form on a blank EVM token. */
  add: () => void;
  /** Opens the form on an existing asset. */
  edit: (asset: SupportedAsset) => void;
  /**
   * Opens the form on the asset with this identifier, fetching it first.
   *
   * @remarks
   * A no-op for a null identifier or one the backend does not know, so a stale link leaves the form
   * closed rather than opening it empty.
   */
  editAsset: (assetId: Nullable<string>) => Promise<void>;
  /** True when the open form edits an existing asset rather than creating one. */
  editMode: Readonly<Ref<boolean>>;
  /** The asset the form is bound to; undefined closes it. */
  modelValue: Ref<SupportedAsset | undefined>;
}

/**
 * Drives the managed-asset add/edit form: which asset it holds, whether that is a create or an
 * edit, and the asset types it offers.
 *
 * @remarks
 * The asset types are read once on mount. A failure there is reported but not fatal: the form still
 * opens, with an empty type list, rather than the page refusing to load.
 *
 * @returns the form's bindings; `identifier` is watched, so a route change reopens the form
 */
export function useManagedAssetForm(identifier: MaybeRefOrGetter<Nullable<string>>): UseManagedAssetFormReturn {
  const modelValue = ref<SupportedAsset>();
  const editMode = shallowRef<boolean>(false);
  const assetTypes = ref<string[]>([]);

  const { t } = useI18n({ useScope: 'global' });
  const { getAssetTypes, queryAllAssets } = useAssetManagementApi();
  const { setMessage } = useMessageStore();

  function add(): void {
    set(modelValue, emptyAsset());
    set(editMode, false);
  }

  function edit(asset: SupportedAsset): void {
    set(modelValue, asset);
    set(editMode, true);
  }

  async function editAsset(assetId: Nullable<string>): Promise<void> {
    if (!assetId)
      return;

    const all = await queryAllAssets({
      identifiers: [assetId],
      limit: 1,
      offset: 0,
    });

    const foundAsset = all.data[0];
    if (foundAsset)
      edit(foundAsset);
  }

  watch(() => toValue(identifier), async (assetId) => {
    await editAsset(assetId);
  });

  onBeforeMount(async () => {
    try {
      set(assetTypes, await getAssetTypes());
    }
    catch (error: unknown) {
      setMessage({
        description: t('asset_form.types.error', { message: getErrorMessage(error) }),
      });
    }
  });

  return {
    add,
    assetTypes: shallowReadonly(assetTypes),
    edit,
    editAsset,
    editMode: readonly(editMode),
    modelValue,
  };
}
