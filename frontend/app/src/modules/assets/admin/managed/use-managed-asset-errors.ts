import type { SupportedAsset } from '@rotki/common';
import type { MaybeRefOrGetter, Ref } from 'vue';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { omit } from 'es-toolkit';

interface ManagedAssetErrorsReturn {
  /** Drops the server errors sitting on the given fields. */
  readonly clearFields: (fields: Array<keyof SupportedAsset>) => void;
}

/**
 * Manages the server errors the form is holding, dropping them in two ways.
 *
 * @remarks
 * Changing the asset type drops all of them, not just the fields the new type shares: each type is
 * checked against its own rules.
 */
export function useManagedAssetErrors(
  errors: Ref<ValidationErrors>,
  assetType: MaybeRefOrGetter<string | null | undefined>,
): ManagedAssetErrorsReturn {
  watch(() => toValue(assetType), () => {
    set(errors, {});
  });

  return {
    clearFields: (fields: Array<keyof SupportedAsset>): void => {
      set(errors, omit(get(errors), fields));
    },
  };
}
