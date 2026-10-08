import type { HistoricalBalanceRow, HistoricalBalancesSummary } from './historical-balances-view';
import { bigNumberify } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import dayjs from 'dayjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { PriceStatus } from './use-historical-balance-values';
import { useHistoricalBalancesExport } from './use-historical-balances-export';

const { download } = vi.hoisted(() => ({
  download: vi.fn<(text: string, filename: string, type?: string) => void>(),
}));

vi.mock('@/modules/core/common/file/download', () => ({ downloadFileByTextContent: download }));
vi.mock('@/modules/settings/use-setting', async () => {
  const { ref: settingRef } = await import('vue');
  return {
    useSetting: (key: string): unknown => settingRef(key === 'csvExportDelimiter' ? ';' : 'EUR'),
  };
});
vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): Record<string, unknown> => ({ getAssetField: (asset: string): string => asset }),
}));

const ETH: HistoricalBalanceRow = {
  amount: bigNumberify('1'),
  asset: 'ETH',
  buckets: [],
  members: ['ETH'],
  partial: false,
  price: bigNumberify('2000'),
  priceStatus: PriceStatus.PRICED,
  value: bigNumberify('2000'),
};

const loading = ref<boolean>(false);
const processingRequired = ref<boolean>(false);
const rows = ref<HistoricalBalanceRow[]>([]);
const summary = ref<HistoricalBalancesSummary>({ missingCount: 0, pendingCount: 0, spamCount: 0, total: bigNumberify('2000') });
const locations = ref<string[]>([]);

function create(): ReturnType<typeof useHistoricalBalancesExport> {
  return useHistoricalBalancesExport({
    accounts: [],
    loading,
    locations,
    processingRequired,
    rows,
    search: '',
    summary,
    timestamp: dayjs('2024-12-31T23:59:59').unix(),
  });
}

describe('useHistoricalBalancesExport', () => {
  beforeEach(() => {
    download.mockReset();
    set(loading, false);
    set(processingRequired, false);
    set(rows, [ETH]);
    set(summary, { ...get(summary), pendingCount: 0 });
    set(locations, []);
  });

  it('should offer the export once the day is loaded, processed and fully priced', () => {
    expect(get(create().blockedReason)).toBeUndefined();
  });

  it.each([
    ['loading', (): void => set(loading, true), 'historical_balances.export.blocked.loading'],
    ['unprocessed events', (): void => set(processingRequired, true), 'historical_balances.export.blocked.processing'],
    ['a price still loading', (): void => set(summary, { ...get(summary), pendingCount: 1 }), 'historical_balances.export.blocked.pending'],
    ['no rows', (): void => set(rows, []), 'historical_balances.export.blocked.empty'],
  ])('should hold the export back while there is %s', (_, arrange, reason) => {
    arrange();

    expect(get(create().blockedReason)).toBe(reason);
  });

  it('should download the day as CSV in the user\'s delimiter, named after the day and any filter', () => {
    set(locations, ['ethereum', 'optimism']);
    create().exportCsv();

    expect(download).toHaveBeenCalledOnce();
    const [text, filename, type] = download.mock.calls[0];
    expect(filename).toBe('historical-balances-2024-12-31.csv');
    expect(type).toBe('text/csv');
    expect(text.startsWith('asset;symbol;amount;price_eur;value_eur;status\n')).toBe(true);
    expect(text).toContain('\nfilter;location: ethereum, optimism\n');
  });
});
