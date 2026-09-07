import type { ActionStatus } from '@/modules/core/common/action';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SkipState, useAccountSkipQueries } from '@/modules/accounts/table/use-account-skip-queries';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const write = vi.fn<(key: string, value: Record<string, string[]>) => Promise<ActionStatus>>(
  async () => ({ success: true }),
);
const setMessage = vi.fn();

vi.mock('@/modules/settings/settings-writer', () => ({
  useSettingsWriter: (): { write: typeof write } => ({ write }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): { setMessage: typeof setMessage } => ({ setMessage }),
}));

describe('useAccountSkipQueries', () => {
  const ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

  function setDisabled(value: Record<string, string[]>): void {
    const store = useSettingsRepo();
    store.updateGeneral({ ...store.general, disabledChainQueries: value });
  }

  function writtenPayload(): Record<string, string[]> {
    const call = write.mock.lastCall;
    expect(call).toBeDefined();
    return call?.[1] ?? {};
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    write.mockResolvedValue({ success: true });
  });

  describe('state', () => {
    it('should be none when no chain of the row is skipped', () => {
      const { locked, state } = useAccountSkipQueries(ADDRESS, ['eth', 'optimism']);
      expect(get(state)).toBe(SkipState.NONE);
      expect(get(locked)).toBe(false);
    });

    it('should be partial when only some chains are skipped', () => {
      setDisabled({ optimism: [ADDRESS] });
      expect(get(useAccountSkipQueries(ADDRESS, ['eth', 'optimism']).state)).toBe(SkipState.PARTIAL);
    });

    it('should be all when every chain is skipped', () => {
      setDisabled({ eth: [ADDRESS], optimism: [ADDRESS] });
      expect(get(useAccountSkipQueries(ADDRESS, ['eth', 'optimism']).state)).toBe(SkipState.ALL);
    });

    it('should ignore a chain switched off whole, which the row cannot act on', () => {
      setDisabled({ base: [], eth: [ADDRESS] });
      expect(get(useAccountSkipQueries(ADDRESS, ['eth', 'base']).state)).toBe(SkipState.ALL);
    });

    it('should lock the row when every chain in scope is switched off whole', () => {
      setDisabled({ base: [] });
      const { locked, state } = useAccountSkipQueries(ADDRESS, ['base']);
      expect(get(locked)).toBe(true);
      expect(get(state)).toBe(SkipState.NONE);
    });
  });

  describe('items', () => {
    it('should list every chain of the row, marking the ones off whole', () => {
      setDisabled({ base: [], eth: [ADDRESS] });

      expect(get(useAccountSkipQueries(ADDRESS, ['eth', 'base', 'optimism']).items)).toEqual([
        { chain: 'eth', name: 'Eth', skipped: true, wholeChain: false },
        { chain: 'base', name: 'Base', skipped: false, wholeChain: true },
        { chain: 'optimism', name: 'Optimism', skipped: false, wholeChain: false },
      ]);
    });
  });

  describe('writes', () => {
    it('should skip one chain without touching the others', async () => {
      setDisabled({ eth: [ADDRESS] });

      await useAccountSkipQueries(ADDRESS, ['eth', 'optimism']).toggleChain('optimism');

      expect(writtenPayload()).toEqual({ eth: [ADDRESS], optimism: [ADDRESS] });
    });

    it('should resume one chain without touching the others', async () => {
      setDisabled({ eth: [ADDRESS], optimism: [ADDRESS] });

      await useAccountSkipQueries(ADDRESS, ['eth', 'optimism']).toggleChain('eth');

      expect(writtenPayload()).toEqual({ optimism: [ADDRESS] });
    });

    it('should skip the rest from a partial state, rather than resume', async () => {
      setDisabled({ optimism: [ADDRESS] });

      await useAccountSkipQueries(ADDRESS, ['eth', 'optimism']).toggleAll();

      expect(writtenPayload()).toEqual({ eth: [ADDRESS], optimism: [ADDRESS] });
    });

    it('should resume every chain once they are all skipped', async () => {
      setDisabled({ eth: [ADDRESS], optimism: [ADDRESS] });

      await useAccountSkipQueries(ADDRESS, ['eth', 'optimism']).toggleAll();

      expect(writtenPayload()).toEqual({});
    });

    it('should report a rejected write', async () => {
      write.mockResolvedValue({ message: 'nope', success: false });

      await useAccountSkipQueries(ADDRESS, ['eth']).toggleChain('eth');

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ description: 'nope', success: false }));
    });

    it('should not report a write that succeeded', async () => {
      const { pending, toggleChain } = useAccountSkipQueries(ADDRESS, ['eth']);

      await toggleChain('eth');

      expect(setMessage).not.toHaveBeenCalled();
      expect(get(pending)).toBe(false);
    });
  });
});
