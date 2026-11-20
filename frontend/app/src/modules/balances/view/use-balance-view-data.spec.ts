import { bigNumberify, Zero } from '@rotki/common';
import { createTestManualBalance } from '@test/utils/create-data';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type Ref, ref } from 'vue';
import { BalanceType } from '@/modules/balances/types/balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useBalanceViewData } from '@/modules/balances/view/use-balance-view-data';

const DEBT_TOKEN = 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8';
const HISTORY_ONLY_DEBT = 'eip155:1/erc20:0x72E95b8931767C79bA4EeE721354d6E99a61D004';
const ACCOUNT = '0x006a3aD7251db5D12992B62cce26252ac58492Dd';

const h = await vi.hoisted(async () => {
  const { ref: vueRef } = await import('vue');
  return { threshold: vueRef<string | undefined>(undefined) };
});

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): object => ({ getAssetPrice: (asset: string) => (asset === 'ETH' ? bigNumberify('2000') : bigNumberify('1')) }),
}));
vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): object => ({ assetCollections: ref({}), assets: ref({}), ignoredAssets: ref([]), isAssetIgnored: (): boolean => false }),
}));
vi.mock('@/modules/assets/use-resolve-asset-identifier', () => ({
  useResolveAssetIdentifier: () => (asset: string): string => asset,
}));
vi.mock('@/modules/assets/amount-display/use-usd-value-threshold', () => ({
  useValueThreshold: (): Ref<string | undefined> => h.threshold,
}));
vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ matchChain: (location: string): string | undefined => (location === 'ethereum' ? 'eth' : undefined) }),
}));
vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<boolean> => ref<boolean>(false),
}));
vi.mock('@/modules/statistics/use-statistics-store', () => ({
  useStatisticsStore: (): object => ({ nftValue: ref(Zero), totalNetWorth: ref(bigNumberify('10000')) }),
}));
vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: (): object => ({ accounts: ref({}) }),
}));
vi.mock('@/modules/balances/manual/use-manual-balance-data', () => ({
  useManualBalanceData: (): object => ({ manualBalanceByLocation: ref({}) }),
}));
vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): object => ({ tradeLocations: ref([]) }),
}));

function setSnapshot(entries: { amount: string; asset: string; isLiability: boolean }[]): void {
  useHistoricalSnapshotStore().setSnapshot({
    entries: entries.map(entry => ({ ...entry, amount: bigNumberify(entry.amount), location: 'ethereum', locationLabel: ACCOUNT, protocol: null })),
    processingRequired: false,
    stale: false,
  });
}

function seedPortfolio(historyDebtAmount = '22060.97'): void {
  useBalancesStore().updateBalances('eth', {
    perAccount: {
      eth: {
        [ACCOUNT]: {
          assets: { ETH: { address: { amount: bigNumberify('16'), value: bigNumberify('32000') } } },
          liabilities: {
            [DEBT_TOKEN]: { 'aave-v3': { amount: bigNumberify('22067.19'), value: bigNumberify('22067.19') } },
            DAI: { makerdao: { amount: bigNumberify('1000'), value: bigNumberify('1000') } },
          },
        },
      },
    },
    totals: { assets: {}, liabilities: {} },
  });
  setSnapshot([
    { amount: '16', asset: 'ETH', isLiability: false },
    { amount: historyDebtAmount, asset: DEBT_TOKEN, isLiability: true },
  ]);
}

function viewData(history: boolean): ReturnType<typeof useBalanceViewData> {
  return useBalanceViewData(computed<boolean>(() => history));
}

describe('useBalanceViewData debt token liability routing', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    h.threshold.value = undefined;
  });

  it('should route history debt tokens out of assets and into liabilities alongside live protocol liabilities', () => {
    seedPortfolio();
    const data = viewData(true);

    expect(get(data.balances).map(row => row.asset)).toStrictEqual(['ETH']);
    expect(get(data.comparisons).has(DEBT_TOKEN)).toBe(false);

    const liabilitiesByAsset = new Map(get(data.liabilities).map(row => [row.asset, row.amount.toFixed(2)]));
    expect(liabilitiesByAsset.get(DEBT_TOKEN)).toBe('22060.97');
    expect(liabilitiesByAsset.get('DAI')).toBe('1000.00');
  });

  it('should compare derived debt tokens against live liabilities and subtract them from history net worth', () => {
    seedPortfolio();
    const data = viewData(true);
    const debtComparison = data.getAssetComparison(DEBT_TOKEN);

    expect(debtComparison.history.toFixed(2)).toBe('22060.97');
    expect(debtComparison.queried.toFixed(2)).toBe('22067.19');
    expect(debtComparison.delta.toFixed(2)).toBe('-6.22');
    expect(get(data.netWorth).toFixed(2)).toBe('8939.03');
  });

  it('should resolve liability price info in both history and live views', () => {
    seedPortfolio();

    expect(viewData(true).getAssetPriceInfo(DEBT_TOKEN).amount.toFixed(2)).toBe('22060.97');
    expect(viewData(false).getAssetPriceInfo(DEBT_TOKEN).amount.toFixed(2)).toBe('22067.19');
  });

  it('should pad history-only liabilities at zero in live view and keep liabilitiesHeld true', () => {
    setSnapshot([{ amount: '250', asset: HISTORY_ONLY_DEBT, isLiability: true }]);
    const liveData = viewData(false);

    expect(get(liveData.liabilitiesHeld)).toBe(true);
    expect(get(liveData.liabilities).find(row => row.asset === HISTORY_ONLY_DEBT)?.amount.isZero()).toBe(true);
    expect(get(liveData.liabilityComparisons).get(HISTORY_ONLY_DEBT)?.delta.toNumber()).toBe(250);
  });

  it('should attribute manual liabilities in liabilityComparisons', () => {
    seedPortfolio();
    useBalancesStore().$patch({
      manualLiabilities: [createTestManualBalance('DAI', 500, 500, 'external', BalanceType.LIABILITY, 1)],
    });
    const daiLiability = get(viewData(true).liabilityComparisons).get('DAI');

    expect(daiLiability?.manual.toNumber()).toBe(500);
    expect(daiLiability?.delta.toNumber()).toBe(-500);
  });

  it('should not fall back to live liability when a history-tracked debt token is below the value threshold', () => {
    h.threshold.value = '10';
    seedPortfolio('5');
    const debtComparison = viewData(true).getAssetComparison(DEBT_TOKEN);

    expect(debtComparison.history.isZero()).toBe(true);
    expect(debtComparison.queried.toFixed(2)).toBe('22067.19');
    expect(debtComparison.delta.toFixed(2)).toBe('-22067.19');
  });
});
