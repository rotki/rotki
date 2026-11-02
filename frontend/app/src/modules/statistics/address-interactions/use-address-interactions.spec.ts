import type { RotkiApi } from '@/modules/core/api/rotki-api';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it, vi } from 'vitest';
import { useAddressInteractions } from './use-address-interactions';

const { apiGet, fetchEnsNames } = vi.hoisted(() => ({
  fetchEnsNames: vi.fn<(payload: { address: string; blockchain: string | null }[]) => Promise<void>>().mockResolvedValue(undefined),
  apiGet: vi.fn<() => Promise<unknown>>(),
}));

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: createMock<RotkiApi>({ get: apiGet }),
}));

vi.mock('@/modules/accounts/address-book/use-ens-operations', () => ({
  useEnsOperations: (): object => ({ fetchEnsNames }),
}));

describe('use address interactions', () => {
  it('should look up ENS names for every address it loads, once each', async () => {
    apiGet.mockResolvedValue([
      { chain: 'eth', source: '0xa', target: '0xb', txHash: '0x1' },
      { chain: 'optimism', source: '0xa', target: '0xc', txHash: '0x2' },
    ]);
    const { interactions, refresh } = useAddressInteractions();

    await refresh();

    expect(get(interactions)).toHaveLength(2);
    expect(fetchEnsNames).toHaveBeenCalledWith([
      { address: '0xa', blockchain: null },
      { address: '0xb', blockchain: null },
      { address: '0xc', blockchain: null },
    ]);
  });

  it('should retain both bridge legs alongside ordinary transfers', async () => {
    const rows = [
      { chain: 'eth', source: '0xa', target: '0xb', txHash: '0xordinary' },
      { chain: 'eth', source: '0xb', target: '0xa', targetChain: 'optimism', targetTxHash: '0xwithdrawal', txHash: '0xdeposit' },
    ];
    apiGet.mockResolvedValue(rows);
    const { interactions, refresh } = useAddressInteractions();

    await refresh();

    expect(get(interactions)).toEqual(rows);
  });
});
