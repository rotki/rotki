import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { describe, expect, it } from 'vitest';
import { useManagedAssetErrors } from '@/modules/assets/admin/managed/use-managed-asset-errors';

describe('useManagedAssetErrors', () => {
  function setup(assetTypeValue = 'evm token'): {
    assetType: Ref<string | null | undefined>;
    clearFields: ReturnType<typeof useManagedAssetErrors>['clearFields'];
    errors: Ref<ValidationErrors>;
  } {
    const errors = ref<ValidationErrors>({
      address: ['not an address'],
      name: ['required'],
    });
    const assetType = ref<string | null | undefined>(assetTypeValue);
    const { clearFields } = useManagedAssetErrors(errors, assetType);
    return { assetType, clearFields, errors };
  }

  it('should drop every server error when the asset type changes', async () => {
    const { assetType, errors } = setup();

    set(assetType, 'solana token');
    await nextTick();

    expect(get(errors)).toStrictEqual({});
  });

  it('should keep the server errors while the asset type holds', async () => {
    const { assetType, errors } = setup();

    set(assetType, 'evm token');
    await nextTick();

    expect(get(errors)).toStrictEqual({
      address: ['not an address'],
      name: ['required'],
    });
  });

  it('should drop only the named fields when clearing individually', () => {
    const { clearFields, errors } = setup();

    clearFields(['address']);

    expect(get(errors)).toStrictEqual({ name: ['required'] });
  });
});
