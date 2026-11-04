import type { ImportLocationResolution } from '@/modules/user-data/import-location-types';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useImportLocationMapping } from '@/modules/user-data/use-import-location-mapping';

const { checkImportFileLocations, checkImportLocations, setLocationAlias } = vi.hoisted(() => ({
  checkImportFileLocations: vi.fn<(data: FormData) => Promise<ImportLocationResolution[]>>(),
  checkImportLocations: vi.fn<(payload: unknown) => Promise<ImportLocationResolution[]>>(),
  setLocationAlias: vi.fn<(alias: string, locationIdentifier: string) => Promise<boolean>>(),
}));

vi.mock('@/modules/user-data/use-import-data-api', () => ({
  useImportDataApi: (): Record<string, unknown> => ({ checkImportFileLocations, checkImportLocations }),
}));

vi.mock('@/modules/locations/use-location-tree-api', () => ({
  useLocationTreeApi: (): Record<string, unknown> => ({ setLocationAlias }),
}));

const unknown: ImportLocationResolution = { candidates: [], location: null, status: 'unresolved', value: 'luno' };
const resolved: ImportLocationResolution = { candidates: [], location: 'kraken', status: 'resolved', value: 'Kraken' };

describe('useImportLocationMapping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setLocationAlias.mockResolvedValue(true);
  });

  it('should check a file by its path with the mappings chosen so far, keeping only the values left unplaced', async () => {
    checkImportLocations.mockResolvedValue([resolved, unknown]);
    const { checkLocations, modelMappings, pending } = useImportLocationMapping();
    set(modelMappings, { cex: 'external' });

    expect(await checkLocations('rotki_events', { path: '/tmp/a.csv' })).toBe('unplaced');
    expect(checkImportLocations).toHaveBeenCalledExactlyOnceWith({ file: '/tmp/a.csv', locationMappings: { cex: 'external' }, source: 'rotki_events' });
    expect(get(pending)).toEqual([unknown]);
  });

  it('should check an upload through its form data, and tell when every value resolves', async () => {
    checkImportFileLocations.mockResolvedValue([resolved]);
    const formData = new FormData();

    expect(await useImportLocationMapping().checkLocations('rotki_trades', { formData })).toBe('placed');
    expect(checkImportFileLocations).toHaveBeenCalledExactlyOnceWith(formData);
    expect(checkImportLocations).not.toHaveBeenCalled();
  });

  it('should miss a choice until every value the check could not place has a location', async () => {
    const ambiguous: ImportLocationResolution = { candidates: ['custom:a', 'custom:b'], location: null, status: 'ambiguous', value: 'Harbor' };
    checkImportLocations.mockResolvedValue([resolved, unknown, ambiguous]);
    const { checkLocations, choicesMissing, modelMappings } = useImportLocationMapping();
    expect(get(choicesMissing)).toBe(false);

    await checkLocations('rotki_events', { path: '/tmp/a.csv' });
    expect(get(choicesMissing)).toBe(true);

    set(modelMappings, { luno: 'external', Harbor: '' });
    expect(get(choicesMissing)).toBe(true);

    set(modelMappings, { luno: 'external', Harbor: 'custom:b' });
    expect(get(choicesMissing)).toBe(false);
  });

  it('should save each chosen location as an alias under its trimmed value, but not an empty value or an empty choice', async () => {
    const { modelMappings, rememberAliases } = useImportLocationMapping();
    set(modelMappings, { '': 'external', 'cex': '', ' luno ': 'custom:luno' });

    rememberAliases(vi.fn());
    await flushPromises();

    expect(setLocationAlias).toHaveBeenCalledExactlyOnceWith('luno', 'custom:luno');
  });

  it('should save no alias when the user asked not to', async () => {
    const { modelMappings, modelSaveAsAliases, rememberAliases } = useImportLocationMapping();
    set(modelMappings, { luno: 'custom:luno' });
    set(modelSaveAsAliases, false);

    rememberAliases(vi.fn());
    await flushPromises();

    expect(setLocationAlias).not.toHaveBeenCalled();
  });

  it('should hand back why the aliases could not be saved', async () => {
    setLocationAlias.mockRejectedValue(new Error('Location custom:luno is archived'));
    const onFailure = vi.fn<(error: string) => void>();
    const { modelMappings, rememberAliases } = useImportLocationMapping();
    set(modelMappings, { luno: 'custom:luno' });

    rememberAliases(onFailure);
    await flushPromises();

    expect(onFailure).toHaveBeenCalledExactlyOnceWith('luno: Location custom:luno is archived');
  });

  it('should name only the aliases that could not be saved', async () => {
    setLocationAlias.mockImplementation(async (alias: string) => {
      if (alias === 'cex')
        throw new Error('Location external is archived');
      return true;
    });
    const onFailure = vi.fn<(failed: string) => void>();
    const { modelMappings, rememberAliases } = useImportLocationMapping();
    set(modelMappings, { cex: 'external', luno: 'custom:luno' });

    rememberAliases(onFailure);
    await flushPromises();

    expect(setLocationAlias).toHaveBeenCalledTimes(2);
    expect(onFailure).toHaveBeenCalledExactlyOnceWith('cex: Location external is archived');
  });

  it('should drop a check that ends after the file was replaced, leaving nothing to map', async () => {
    let answer: (found: ImportLocationResolution[]) => void = () => {};
    checkImportLocations.mockReturnValue(new Promise((resolve) => {
      answer = resolve;
    }));
    const { checkLocations, choicesMissing, pending, reset } = useImportLocationMapping();
    const check = checkLocations('rotki_events', { path: '/tmp/a.csv' });

    reset();
    answer([unknown]);

    expect(await check).toBe('replaced');
    expect(get(pending)).toEqual([]);
    expect(get(choicesMissing)).toBe(false);
  });

  it('should forget the check and the choices for the next file', async () => {
    checkImportLocations.mockResolvedValue([unknown]);
    const { checkLocations, modelMappings, pending, reset } = useImportLocationMapping();
    await checkLocations('rotki_events', { path: '/tmp/a.csv' });
    set(modelMappings, { luno: 'external' });

    reset();

    expect(get(pending)).toEqual([]);
    expect(get(modelMappings)).toEqual({});
  });
});
