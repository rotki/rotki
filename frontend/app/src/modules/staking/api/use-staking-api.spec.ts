import type { RotkiApi } from '@/modules/core/api/rotki-api';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';
import { useStakingApi } from '@/modules/staking/api/use-staking-api';

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/modules/core/api/rotki-api', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/api/rotki-api')>(),
  api: createMock<RotkiApi>({ get: mockGet }),
}));

describe('useStakingApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should start the solana stake accounts query as a task', async () => {
    mockGet.mockResolvedValue({ taskId: 7 });
    const { fetchSolanaStakeAccounts } = useStakingApi();
    const result = await fetchSolanaStakeAccounts();

    expect(mockGet).toHaveBeenCalledWith('/blockchains/solana/stake/accounts', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    expect(result).toEqual({ taskId: 7 });
  });

  it('should start the hyperliquid summaries query as a task', async () => {
    mockGet.mockResolvedValue({ taskId: 8 });
    const { fetchHyperliquidStakingSummaries } = useStakingApi();
    const result = await fetchHyperliquidStakingSummaries();

    expect(mockGet).toHaveBeenCalledWith('/blockchains/hyperliquid/stake/summary', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    expect(result).toEqual({ taskId: 8 });
  });
});
