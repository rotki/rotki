import type { SupportedAsset, UnderlyingToken } from '@rotki/common';
import type { MaybeRefOrGetter, Ref } from 'vue';
import { omit } from 'es-toolkit';
import { buildManagedAssetPayload } from '@/modules/assets/admin/managed/managed-asset-payload';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';

interface ManagedAssetSaveOptions {
  readonly asset: Ref<SupportedAsset>;
  readonly underlyingTokens: Ref<UnderlyingToken[]>;
  readonly editMode: MaybeRefOrGetter<boolean>;
}

interface ManagedAssetSaveReturn {
  /** Writes the asset and answers with the identifier it now has. */
  readonly saveAsset: () => Promise<string>;
}

/**
 * Persists the asset the form is editing.
 *
 * Adding and editing differ in more than the endpoint: an edit sends the identifier it already has,
 * while an add must not send one at all and learns it from the response.
 */
export function useManagedAssetSave(options: ManagedAssetSaveOptions): ManagedAssetSaveReturn {
  const { asset, editMode, underlyingTokens } = options;

  const { addAsset, editAsset } = useAssetManagementApi();

  async function saveAsset(): Promise<string> {
    const payload = buildManagedAssetPayload(get(asset), get(underlyingTokens));

    if (toValue(editMode)) {
      const { identifier } = get(asset);
      await editAsset({ ...payload, identifier });
      return identifier;
    }

    const { identifier } = await addAsset(omit(payload, ['identifier']));
    return identifier;
  }

  return { saveAsset };
}
