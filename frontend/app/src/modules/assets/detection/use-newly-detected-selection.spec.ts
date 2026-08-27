import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NewDetectedTokenKind } from '@/modules/assets/detection/types';
import { type Filters, NewlyDetectedFilterKeys } from '@/modules/assets/detection/use-newly-detected-filter';
import { useNewlyDetectedSelection } from '@/modules/assets/detection/use-newly-detected-selection';

const getAllIdentifiers = vi.fn<(kind?: NewDetectedTokenKind) => Promise<string[]>>();
const removeNewDetectedTokens = vi.fn<(ids: string[]) => Promise<void>>();
const markAssetsAsSpam = vi.fn<(ids: string[]) => Promise<{ success: boolean }>>();

vi.mock('@/modules/assets/detection/use-newly-detected-tokens', () => ({
  useNewlyDetectedTokens: (): Record<string, unknown> => ({
    getAllIdentifiers: async (kind?: NewDetectedTokenKind): Promise<string[]> => getAllIdentifiers(kind),
    removeNewDetectedTokens: async (ids: string[]): Promise<void> => removeNewDetectedTokens(ids),
  }),
}));

vi.mock('@/modules/assets/use-spam-asset', () => ({
  useSpamAsset: (): Record<string, unknown> => ({
    markAssetsAsSpam: async (ids: string[]): Promise<{ success: boolean }> => markAssetsAsSpam(ids),
  }),
}));

describe('useNewlyDetectedSelection', () => {
  const refetch = vi.fn<() => Promise<void>>();

  beforeEach(() => {
    vi.clearAllMocks();
    getAllIdentifiers.mockResolvedValue(['a', 'b']);
    removeNewDetectedTokens.mockResolvedValue();
    markAssetsAsSpam.mockResolvedValue({ success: true });
    refetch.mockResolvedValue();
  });

  function setup(filters: Filters = {}): ReturnType<typeof useNewlyDetectedSelection> {
    return useNewlyDetectedSelection({ filters, found: 2, refetch });
  }

  it('should select all of the narrowed kind, meaning everything the table is showing rather than every kind', async () => {
    const { modelSelected, toggleSelection } = setup({
      [NewlyDetectedFilterKeys.TOKEN_KIND]: NewDetectedTokenKind.SOLANA,
    });

    await toggleSelection();

    expect(getAllIdentifiers).toHaveBeenCalledWith(NewDetectedTokenKind.SOLANA);
    expect(get(modelSelected)).toStrictEqual(['a', 'b']);
  });

  it('should ask for every kind when no pill is set', async () => {
    const { toggleSelection } = setup();

    await toggleSelection();

    expect(getAllIdentifiers).toHaveBeenCalledWith(undefined);
  });

  it('should clear the selection when everything is already selected', async () => {
    const { modelSelected, toggleSelection } = setup();

    await toggleSelection();
    await toggleSelection();

    expect(get(modelSelected)).toStrictEqual([]);
  });

  it('should clear the selection when the narrowing changes', async () => {
    const filters = ref<Filters>({});
    const { modelSelected, toggleSelection } = useNewlyDetectedSelection({ filters, found: 2, refetch });

    await toggleSelection();
    expect(get(modelSelected)).toStrictEqual(['a', 'b']);

    set(filters, { [NewlyDetectedFilterKeys.TOKEN_KIND]: NewDetectedTokenKind.SOLANA });
    await nextTick();

    expect(get(modelSelected)).toStrictEqual([]);
  });

  it('should report everything selected only when the count matches what was found', async () => {
    const { allSelected, toggleSelection } = setup();

    expect(get(allSelected)).toBe(false);
    await toggleSelection();
    expect(get(allSelected)).toBe(true);
  });

  it('should remove the selection and refetch', async () => {
    const { modelSelected, removeTokens, toggleSelection } = setup();

    await toggleSelection();
    await removeTokens();

    expect(removeNewDetectedTokens).toHaveBeenCalledWith(['a', 'b']);
    expect(get(modelSelected)).toStrictEqual([]);
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it('should remove a single row without touching the selection set', async () => {
    const { removeTokens } = setup();

    await removeTokens('one');

    expect(removeNewDetectedTokens).toHaveBeenCalledWith(['one']);
  });

  it('should remove the rows it marked as spam, but only once the marking succeeded', async () => {
    const { markAsSpam } = setup();

    await markAsSpam(['a', 'a', 'b']);

    expect(markAssetsAsSpam).toHaveBeenCalledWith(['a', 'b']);
    expect(removeNewDetectedTokens).toHaveBeenCalledWith(['a', 'b']);
  });

  it('should keep the rows when marking them as spam failed', async () => {
    markAssetsAsSpam.mockResolvedValue({ success: false });
    const { markAsSpam } = setup();

    await markAsSpam(['a']);

    expect(removeNewDetectedTokens).not.toHaveBeenCalled();
  });
});
