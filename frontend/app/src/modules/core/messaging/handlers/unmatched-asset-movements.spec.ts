import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createUnmatchedAssetMovementsHandler } from '@/modules/core/messaging/handlers/unmatched-asset-movements';

const { fetchUnmatchedAssetMovements } = vi.hoisted(() => ({
  fetchUnmatchedAssetMovements: vi.fn<(onlyIgnored?: boolean) => Promise<void>>(),
}));

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({ fetchUnmatchedAssetMovements }),
}));

describe('createUnmatchedAssetMovementsHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchUnmatchedAssetMovements.mockResolvedValue();
  });

  it('should re-read the unmatched movements the row counts and create no notification', async () => {
    const handler = createUnmatchedAssetMovementsHandler();

    const result = await handler.handle({ count: 2 });

    expect(result).toBeNull();
    expect(fetchUnmatchedAssetMovements).toHaveBeenCalledExactlyOnceWith();
  });

  it('should re-read on a zero count too, so a row raised before goes away', async () => {
    const handler = createUnmatchedAssetMovementsHandler();

    await handler.handle({ count: 0 });

    expect(fetchUnmatchedAssetMovements).toHaveBeenCalledOnce();
  });
});
