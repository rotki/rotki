import type { AssetBalancesDisplay } from '@/modules/balances/types/balances';
import { describe, expect, it, vi } from 'vitest';
import { TableColumn } from '@/modules/core/table/table-column';
import { useAssetBalancesHeaders } from './use-asset-balances-headers';

const { isMdAndDown } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { isMdAndDown: ref<boolean>(false) };
});

vi.mock('@rotki/ui-library', async importOriginal => ({
  ...await importOriginal<typeof import('@rotki/ui-library')>(),
  useBreakpoint: (): object => ({ isMdAndDown }),
}));

function keys(display: AssetBalancesDisplay | undefined, fillsPanel = false): string[] {
  return get(useAssetBalancesHeaders(display, fillsPanel)).map(header => String(header.key));
}

describe('useAssetBalancesHeaders', () => {
  it('should list asset, price, amount and value by default', () => {
    expect(keys(undefined)).toEqual(['asset', 'price', 'amount', 'value']);
  });

  it('should put the location column right after the asset when asked for', () => {
    expect(keys({ showPerProtocol: true })).toEqual(['asset', 'perProtocol', 'price', 'amount', 'value']);
  });

  it('should append the share-of-total columns that are visible', () => {
    const display: AssetBalancesDisplay = {
      visibleColumns: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE, TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP],
    };

    expect(keys(display)).toEqual([
      'asset',
      'price',
      'amount',
      'value',
      'percentageOfTotalNetValue',
      'percentageOfTotalCurrentGroup',
    ]);
  });

  it('should fix the column widths in a panel and let the asset column shrink', () => {
    set(isMdAndDown, false);
    const headers = get(useAssetBalancesHeaders({ showPerProtocol: true }, true));
    const byKey = new Map(headers.map(header => [String(header.key), header]));

    expect(byKey.get('price')?.class).toContain('w-28');
    expect(byKey.get('asset')?.class).not.toContain('w-full');
    expect(byKey.get('asset')?.cellClass).toContain('max-w-0');
  });

  it('should drop location and price from a panel on a narrow screen', () => {
    set(isMdAndDown, true);
    expect(keys({ showPerProtocol: true }, true)).toEqual(['asset', 'amount', 'value']);
  });

  it('should keep every column outside a panel on a narrow screen', () => {
    set(isMdAndDown, true);
    expect(keys({ showPerProtocol: true })).toEqual(['asset', 'perProtocol', 'price', 'amount', 'value']);
  });
});
