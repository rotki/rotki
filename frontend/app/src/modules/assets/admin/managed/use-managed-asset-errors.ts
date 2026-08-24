import type { SupportedAsset } from '@rotki/common';
import type { MaybeRefOrGetter, Ref } from 'vue';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { omit } from 'es-toolkit';

interface ManagedAssetErrorsReturn {
  /** Drops the server errors sitting on the given fields. */
  readonly clearFields: (fields: Array<keyof SupportedAsset>) => void;
}

/**
 * The server errors the form is holding.
 *
 * They are dropped wholesale when the asset type changes, because each type is checked against a
 * different set of rules and what the server said about the last one no longer describes this one.
 * Individual fields are cleared when something fills them in.
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
