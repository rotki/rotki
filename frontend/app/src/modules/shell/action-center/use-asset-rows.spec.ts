import type { EffectScope } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetRows } from '@/modules/shell/action-center/use-asset-rows';

const missingPricesCount = ref<number>(0);
const mappingsCount = ref<number>(0);
const refreshMappings = vi.fn<() => Promise<void>>();
const showMissingPrices = vi.fn<() => void>();

vi.mock('@/modules/assets/prices/missing/use-missing-prices', () => ({
  useMissingPrices: (): object => ({ missingPricesCount }),
}));

vi.mock('@/modules/assets/prices/missing/use-missing-prices-dialog', () => ({
  useMissingPricesDialog: (): object => ({ show: showMissingPrices }),
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-missing-mappings-count', () => ({
  useMissingMappingsCount: (): object => ({ count: mappingsCount, refresh: refreshMappings }),
}));

let scope: EffectScope | undefined;

function assetRows(): ReturnType<typeof useAssetRows> {
  scope = effectScope();
  const result = scope.run(() => useAssetRows());
  assert(result);
  return result;
}

describe('modules/shell/action-center/use-asset-rows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(missingPricesCount, 0);
    set(mappingsCount, 0);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should count the assets an oracle stopped pricing', () => {
    const { rows } = assetRows();
    set(missingPricesCount, 3);

    const row = get(rows).find(({ id }) => id === 'missing-prices');
    assert(row);
    expect(row.count).toBe(3);
    expect(row.title).toBe('action_center.rows.assets.missing_prices.title');
  });

  it('should open the missing prices dialog, closing the center first since the dialog is a surface of its own', () => {
    const row = get(assetRows().rows).find(({ id }) => id === 'missing-prices');
    assert(row);
    assert(row.target.kind === 'run');

    expect(row.target.closesCenter).toBe(true);
    row.target.run();
    expect(showMissingPrices).toHaveBeenCalledOnce();
  });

  it('should keep the unmapped exchange assets row pointing at the mapping page', () => {
    set(mappingsCount, 2);
    const row = get(assetRows().rows).find(({ id }) => id === 'missing-exchange-mappings');
    assert(row);

    expect(row.count).toBe(2);
    expect(row.target).toEqual({ kind: 'route', to: { name: '/asset-manager/more/missing-mappings/' } });
  });
});
