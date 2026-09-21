import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationAliases } from '@/modules/locations/use-location-aliases';

const { deleteLocationAlias, fetchLocationAliases, setLocationAlias } = vi.hoisted(() => ({
  deleteLocationAlias: vi.fn<(alias: string) => Promise<boolean>>(),
  fetchLocationAliases: vi.fn<() => Promise<{ alias: string; locationIdentifier: string }[]>>(),
  setLocationAlias: vi.fn<(alias: string, locationIdentifier: string) => Promise<boolean>>(),
}));

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): Record<string, unknown> => ({ deleteLocationAlias, fetchLocationAliases, setLocationAlias }),
}));

const LUNO = { alias: 'luno', locationIdentifier: 'custom:harbor' };
const CEX = { alias: 'cex', locationIdentifier: 'custom:pier' };

describe('useLocationAliases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should load the aliases and hold loading only while the request runs', async () => {
    let resolve!: (value: typeof LUNO[]) => void;
    fetchLocationAliases.mockReturnValue(new Promise((done) => {
      resolve = done;
    }));
    const { aliases, loading, refreshAliases } = useLocationAliases();

    const pending = refreshAliases();
    expect(get(loading)).toBe(true);
    resolve([LUNO]);
    const outcome = await pending;

    assert(outcome.ok);
    expect(get(loading)).toBe(false);
    expect(get(aliases)).toEqual([LUNO]);
  });

  it('should clear loading and hand back the message when the aliases cannot load', async () => {
    fetchLocationAliases.mockRejectedValue(new Error('backend down'));
    const { aliases, loading, refreshAliases } = useLocationAliases();

    const outcome = await refreshAliases();

    assert(!outcome.ok);
    expect(outcome.error).toBe('backend down');
    expect(get(loading)).toBe(false);
    expect(get(aliases)).toEqual([]);
  });

  it('should trim a saved alias and reload the list after it', async () => {
    setLocationAlias.mockResolvedValue(true);
    fetchLocationAliases.mockResolvedValue([LUNO, CEX]);
    const { aliases, saveAlias } = useLocationAliases();

    const outcome = await saveAlias('  cex  ', 'custom:pier');

    assert(outcome.ok);
    expect(setLocationAlias).toHaveBeenCalledWith('cex', 'custom:pier');
    expect(get(aliases)).toEqual([LUNO, CEX]);
  });

  it('should keep the list as it was when a save is refused', async () => {
    fetchLocationAliases.mockResolvedValue([LUNO]);
    const { aliases, refreshAliases, saveAlias } = useLocationAliases();
    await refreshAliases();
    fetchLocationAliases.mockClear();
    setLocationAlias.mockRejectedValue(new Error('Location custom:gone is archived'));

    const outcome = await saveAlias('cex', 'custom:gone');

    assert(!outcome.ok);
    expect(outcome.error).toBe('Location custom:gone is archived');
    expect(fetchLocationAliases).not.toHaveBeenCalled();
    expect(get(aliases)).toEqual([LUNO]);
  });

  it('should remove an alias as given and reload the list after it', async () => {
    deleteLocationAlias.mockResolvedValue(true);
    fetchLocationAliases.mockResolvedValue([CEX]);
    const { aliases, removeAlias } = useLocationAliases();

    const outcome = await removeAlias('luno');

    assert(outcome.ok);
    expect(deleteLocationAlias).toHaveBeenCalledWith('luno');
    expect(get(aliases)).toEqual([CEX]);
  });
});
