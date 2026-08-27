import { describe, expect, it } from 'vitest';
import { useCustomAssetFields } from '@/modules/assets/admin/custom/use-custom-asset-fields';
import '@test/i18n';

describe('useCustomAssetFields', () => {
  it('should offer the types it was given', () => {
    const fields = useCustomAssetFields(['fiat', 'stock']);
    const type = get(fields).find(field => field.key === 'custom_asset_type');

    expect(type?.suggest?.()).toStrictEqual(['fiat', 'stock']);
  });

  it('should follow a reactive list of types, so one created after the bar mounted is still offered', () => {
    const types = ref<string[]>(['fiat']);
    const fields = useCustomAssetFields(types);

    set(types, ['stock']);

    const type = get(fields).find(field => field.key === 'custom_asset_type');
    expect(type?.suggest?.()).toStrictEqual(['stock']);
    expect(type?.validate?.('stock')).toBe(true);
    expect(type?.validate?.('fiat')).toBe(false);
  });
});
