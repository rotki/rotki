import type { ImportLocationResolution } from '@/modules/user-data/use-import-data-api';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useImportLocationMapping } from '@/modules/user-data/use-import-location-mapping';

const { preflightImport, preflightImportFile, setLocationAlias } = vi.hoisted(() => ({
  preflightImport: vi.fn(),
  preflightImportFile: vi.fn(),
  setLocationAlias: vi.fn(),
}));

vi.mock('@/modules/user-data/use-import-data-api', () => ({
  useImportDataApi: (): Record<string, unknown> => ({ preflightImport, preflightImportFile }),
}));

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): Record<string, unknown> => ({ setLocationAlias }),
}));

const kraken: ImportLocationResolution = { candidates: [], location: 'kraken', status: 'resolved', value: 'kraken' };
const luno: ImportLocationResolution = { candidates: [], location: null, status: 'unresolved', value: 'luno' };

describe('useImportLocationMapping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should import right away when every location resolves', async () => {
    preflightImport.mockResolvedValue([kraken]);
    const { pending, resolveLocations } = useImportLocationMapping();

    expect(await resolveLocations('rotki_events', { path: '/events.csv' })).toEqual({ mappings: {}, proceed: true });
    expect(preflightImport).toHaveBeenCalledWith({ file: '/events.csv', source: 'rotki_events' });
    expect(get(pending)).toBeUndefined();
  });

  it('should wait for the user to map the unresolved values, then save them as aliases once asked', async () => {
    preflightImportFile.mockResolvedValue([kraken, luno]);
    const { confirmMappings, pending, rememberAliases, resolveLocations } = useImportLocationMapping();

    const outcome = resolveLocations('rotki_events', { file: new File(['x'], 'events.csv') });
    await vi.waitFor(() => expect(get(pending)).toEqual([luno]));
    confirmMappings({ luno: 'external' }, true);

    expect(await outcome).toEqual({ mappings: { luno: 'external' }, proceed: true });
    expect(get(pending)).toBeUndefined();
    await rememberAliases();
    expect(setLocationAlias).toHaveBeenCalledExactlyOnceWith('luno', 'external');
    await rememberAliases();
    expect(setLocationAlias).toHaveBeenCalledOnce();
  });

  it('should not import when the user cancels, and save no alias not asked for', async () => {
    preflightImport.mockResolvedValue([luno]);
    const { cancelMappings, confirmMappings, pending, rememberAliases, resolveLocations } = useImportLocationMapping();

    const cancelled = resolveLocations('rotki_trades', { path: '/trades.csv' });
    await vi.waitFor(() => expect(get(pending)).toBeDefined());
    cancelMappings();
    expect(await cancelled).toEqual({ proceed: false });

    const confirmed = resolveLocations('rotki_trades', { path: '/trades.csv' });
    await vi.waitFor(() => expect(get(pending)).toBeDefined());
    confirmMappings({ luno: 'external' }, false);
    await confirmed;
    await rememberAliases();
    expect(setLocationAlias).not.toHaveBeenCalled();
  });

  it('should report a failed preflight instead of importing', async () => {
    preflightImport.mockRejectedValue(new Error('Could not read the file'));
    const outcome = await useImportLocationMapping().resolveLocations('rotki_events', { path: '/events.csv' });
    assert(!outcome.proceed);
    expect(outcome.error).toBe('Could not read the file');
  });
});
