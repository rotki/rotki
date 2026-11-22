import type { CexMapping, CexMappingDeletePayload } from '@/modules/assets/types';
import type { MissingMapping } from '@/modules/user-data/schemas';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePruneResolvedMappings } from '@/modules/assets/admin/missing-mappings/use-prune-resolved-mappings';
import { endSession } from '@/modules/core/session/session-lifecycle';

const { getAll, logError, removeByIds, resolveCexSymbols } = vi.hoisted(() => ({
  getAll: vi.fn<() => Promise<MissingMapping[]>>(),
  logError: vi.fn(),
  removeByIds: vi.fn<(ids: number[]) => Promise<void>>(),
  resolveCexSymbols: vi.fn<(payload: CexMappingDeletePayload[]) => Promise<CexMapping[]>>(),
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-missing-mappings-db', () => ({
  useMissingMappingsDB: (): object => ({ getAll, removeByIds }),
}));

vi.mock('@/modules/assets/api/use-asset-cex-mapping-api', () => ({
  useAssetCexMappingApi: (): object => ({ resolveCexSymbols }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { error: logError },
}));

function record(id: number, location: string, identifier: string): MissingMapping {
  return { details: 'balance query', id, identifier, location, name: location };
}

describe('modules/assets/admin/missing-mappings/use-prune-resolved-mappings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    removeByIds.mockResolvedValue();
  });

  it('should not ask the backend when nothing is recorded', async () => {
    getAll.mockResolvedValue([]);

    expect(await usePruneResolvedMappings().prune()).toBe(0);
    expect(resolveCexSymbols).not.toHaveBeenCalled();
    expect(removeByIds).not.toHaveBeenCalled();
  });

  it('should ask about every record and delete only those that resolve on their own exchange', async () => {
    getAll.mockResolvedValue([
      record(1, 'binance', 'BTTC'),
      record(2, 'kraken', 'BTTC'),
      record(3, 'kraken', 'NOPE'),
    ]);
    resolveCexSymbols.mockResolvedValue([
      { asset: 'BTT', location: 'binance', locationSymbol: 'BTTC' },
    ]);

    expect(await usePruneResolvedMappings().prune()).toBe(1);
    expect(resolveCexSymbols).toHaveBeenCalledExactlyOnceWith([
      { location: 'binance', locationSymbol: 'BTTC' },
      { location: 'kraken', locationSymbol: 'BTTC' },
      { location: 'kraken', locationSymbol: 'NOPE' },
    ]);
    expect(removeByIds).toHaveBeenCalledExactlyOnceWith([1]);
  });

  it('should delete nothing when no record resolves', async () => {
    getAll.mockResolvedValue([record(1, 'kraken', 'NOPE')]);
    resolveCexSymbols.mockResolvedValue([]);

    expect(await usePruneResolvedMappings().prune()).toBe(0);
    expect(removeByIds).not.toHaveBeenCalled();
  });

  it('should keep every record and log when the backend check fails', async () => {
    getAll.mockResolvedValue([record(1, 'binance', 'BTTC')]);
    resolveCexSymbols.mockRejectedValue(new Error('offline'));

    expect(await usePruneResolvedMappings().prune()).toBe(0);
    expect(removeByIds).not.toHaveBeenCalled();
    expect(logError).toHaveBeenCalledOnce();
  });

  it('should delete nothing when the session ends while the backend answers', async () => {
    getAll.mockResolvedValue([record(1, 'binance', 'BTTC')]);
    resolveCexSymbols.mockImplementation(async () => {
      endSession();
      return [{ asset: 'BTT', location: 'binance', locationSymbol: 'BTTC' }];
    });

    expect(await usePruneResolvedMappings().prune()).toBe(0);
    expect(removeByIds).not.toHaveBeenCalled();
  });
});
