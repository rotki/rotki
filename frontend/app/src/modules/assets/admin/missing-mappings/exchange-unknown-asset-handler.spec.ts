import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createExchangeUnknownAssetHandler } from '@/modules/assets/admin/missing-mappings/exchange-unknown-asset-handler';

const { put, refresh } = vi.hoisted(() => ({
  put: vi.fn<(mapping: object) => Promise<number>>(),
  refresh: vi.fn<() => Promise<void>>(),
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-missing-mappings-db', () => ({
  useMissingMappingsDB: (): object => ({ put }),
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-missing-mappings-count', () => ({
  useMissingMappingsCount: (): object => ({ refresh }),
}));

const report = { details: 'balance query', identifier: 'XYZ', location: 'kraken', name: 'Kraken 1' };

describe('createExchangeUnknownAssetHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    put.mockResolvedValue(1);
    refresh.mockResolvedValue();
  });

  it('should record the mapping, re-read the count the row shows, and create no notification', async () => {
    const handler = createExchangeUnknownAssetHandler();

    const result = await handler.handle(report);

    expect(result).toBeNull();
    expect(put).toHaveBeenCalledExactlyOnceWith(report);
    expect(refresh).toHaveBeenCalledOnce();
    expect(put.mock.invocationCallOrder[0]).toBeLessThan(refresh.mock.invocationCallOrder[0]);
  });

  it('should absorb the rejection of a mapping the table already holds, leaving the count alone', async () => {
    put.mockRejectedValue(new Error('ConstraintError'));
    const handler = createExchangeUnknownAssetHandler();

    await expect(handler.handle(report)).resolves.toBeNull();
    expect(refresh).not.toHaveBeenCalled();
  });
});
