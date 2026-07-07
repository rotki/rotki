import type { Balances } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainTotalSummary } from './use-blockchain-total-summary';

const balances = ref<Balances>({});

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn(() => ({ balances })),
}));

function chain(...assets: { amount: number; value: number }[]): Balances[string] {
  const perAsset: Record<string, Record<string, { amount: ReturnType<typeof bigNumberify>; value: ReturnType<typeof bigNumberify> }>> = {};
  assets.forEach(({ amount, value }, i) => {
    perAsset[`ASSET_${i}`] = { protocol: { amount: bigNumberify(amount), value: bigNumberify(value) } };
  });
  return { '0xacc': { assets: perAsset, liabilities: {} } };
}

describe('useBlockchainTotalSummary', () => {
  beforeEach(() => {
    set(balances, {});
  });

  it('should return no totals for empty balances', () => {
    const { blockchainTotals } = useBlockchainTotalSummary();
    expect(get(blockchainTotals)).toEqual([]);
  });

  it('should sum every asset/protocol value per chain', () => {
    set(balances, {
      eth: chain({ amount: 1, value: 100 }, { amount: 2, value: 50 }),
    });
    const { blockchainTotals } = useBlockchainTotalSummary();
    expect(get(blockchainTotals)).toEqual([
      { chain: 'eth', loading: false, value: bigNumberify(150) },
    ]);
  });

  it('should drop chains that sum to zero', () => {
    set(balances, {
      eth: chain({ amount: 1, value: 100 }),
      gnosis: chain({ amount: 0, value: 0 }),
    });
    const { blockchainTotals } = useBlockchainTotalSummary();
    expect(get(blockchainTotals).map(t => t.chain)).toEqual(['eth']);
  });

  it('should sort chains by descending value', () => {
    set(balances, {
      eth: chain({ amount: 1, value: 100 }),
      gnosis: chain({ amount: 1, value: 300 }),
      base: chain({ amount: 1, value: 200 }),
    });
    const { blockchainTotals } = useBlockchainTotalSummary();
    expect(get(blockchainTotals).map(t => t.chain)).toEqual(['gnosis', 'base', 'eth']);
  });
});
