import type { ActionStatus } from '@/modules/core/common/action';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { skipAddress, unskipAddress, useSkipAddressQueries } from './use-skip-address-queries';

const write = vi.fn<(key: string, value: Record<string, string[]>) => Promise<ActionStatus>>(
  async () => ({ success: true }),
);

vi.mock('@/modules/settings/settings-writer', () => ({
  useSettingsWriter: (): { write: typeof write } => ({ write }),
}));

describe('useSkipAddressQueries', () => {
  const ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
  const OTHER_ADDRESS = '0x71C7656EC7ab88b098defB751B7401B5f6d8976F';

  let composable: ReturnType<typeof useSkipAddressQueries>;

  function setDisabled(value: Record<string, string[]>): void {
    const store = useSettingsRepo();
    store.updateGeneral({ ...store.general, disabledChainQueries: value });
  }

  function writtenPayload(): Record<string, string[]> {
    const call = write.mock.lastCall;
    assert(call, 'expected a write to disabledChainQueries');
    expect(call[0]).toBe('disabledChainQueries');
    return call[1];
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    write.mockClear();
    composable = useSkipAddressQueries();
  });

  describe('isSkipped', () => {
    it('should be true only when every skippable chain excludes the address', () => {
      setDisabled({ eth: [ADDRESS] });
      expect(composable.isSkipped(ADDRESS, ['eth'])).toBe(true);
      expect(composable.isSkipped(ADDRESS, ['eth', 'optimism'])).toBe(false);
    });

    it('should ignore a chain that is switched off whole', () => {
      setDisabled({ base: [], eth: [ADDRESS] });
      expect(composable.isSkipped(ADDRESS, ['eth', 'base'])).toBe(true);
    });

    it('should be false when the only chains in scope are switched off whole', () => {
      setDisabled({ base: [] });
      expect(composable.isSkipped(ADDRESS, ['base'])).toBe(false);
    });
  });

  describe('toggle, adding the rule', () => {
    it('should add the address on every chain in scope', async () => {
      await composable.toggle(ADDRESS, ['eth', 'optimism']);
      expect(writtenPayload()).toEqual({ eth: [ADDRESS], optimism: [ADDRESS] });
    });

    it('should keep the addresses another rule already excludes', async () => {
      setDisabled({ eth: [OTHER_ADDRESS] });
      await composable.toggle(ADDRESS, ['eth']);
      expect(writtenPayload()).toEqual({ eth: [OTHER_ADDRESS, ADDRESS] });
    });

    it('should write into the existing key when the payload spells the chain differently', async () => {
      setDisabled({ polygonPos: [OTHER_ADDRESS] });
      await composable.toggle(ADDRESS, ['polygon_pos']);
      expect(writtenPayload()).toEqual({ polygonPos: [OTHER_ADDRESS, ADDRESS] });
    });

    it('should leave a chain that is switched off whole untouched', async () => {
      setDisabled({ base: [] });
      await composable.toggle(ADDRESS, ['base', 'eth']);
      expect(writtenPayload()).toEqual({ base: [], eth: [ADDRESS] });
    });

    it('should write nothing when every chain in scope is switched off whole', async () => {
      setDisabled({ base: [] });
      await composable.toggle(ADDRESS, ['base']);
      expect(write).not.toHaveBeenCalled();
    });
  });

  describe('toggle, lifting the rule', () => {
    it('should drop the chain key rather than leave an empty array, which would skip the whole chain', async () => {
      setDisabled({ eth: [ADDRESS] });
      await composable.toggle(ADDRESS, ['eth']);
      expect(writtenPayload()).toEqual({});
    });

    it('should keep the other addresses excluded on the chain', async () => {
      setDisabled({ eth: [ADDRESS, OTHER_ADDRESS] });
      await composable.toggle(ADDRESS, ['eth']);
      expect(writtenPayload()).toEqual({ eth: [OTHER_ADDRESS] });
    });

    it('should lift the rule from every chain in scope', async () => {
      setDisabled({ eth: [ADDRESS], optimism: [ADDRESS, OTHER_ADDRESS] });
      await composable.toggle(ADDRESS, ['eth', 'optimism']);
      expect(writtenPayload()).toEqual({ optimism: [OTHER_ADDRESS] });
    });

    it('should match the stored address regardless of case', async () => {
      setDisabled({ eth: [ADDRESS.toLowerCase()] });
      await composable.toggle(ADDRESS, ['eth']);
      expect(writtenPayload()).toEqual({});
    });
  });

  it('should not mutate the stored setting when building the payload', async () => {
    const stored = { eth: [OTHER_ADDRESS] };
    setDisabled(stored);
    await composable.toggle(ADDRESS, ['eth']);
    expect(stored).toEqual({ eth: [OTHER_ADDRESS] });
  });

  describe('concurrent toggles', () => {
    /**
     * Stands in for the real writer, which updates the settings repo before it resolves. The first
     * call is held open by the returned resolver, so the second toggle is asked for while it is
     * still in flight.
     */
    function writeThroughRepo(): () => void {
      let release: () => void = () => {};
      const held = new Promise<void>((resolve) => {
        release = resolve;
      });
      let first = true;
      write.mockImplementation(async (_key, value) => {
        if (first) {
          first = false;
          await held;
        }
        setDisabled(value);
        return { success: true };
      });
      return release;
    }

    it('should not let a second row erase what the first one wrote', async () => {
      const release = writeThroughRepo();

      const first = composable.toggle(ADDRESS, ['eth']);
      const second = composable.toggle(OTHER_ADDRESS, ['optimism']);
      await nextTick();
      release();
      await Promise.all([first, second]);

      expect(writtenPayload()).toEqual({ eth: [ADDRESS], optimism: [OTHER_ADDRESS] });
    });

    it('should keep the queue alive when a write throws rather than answering', async () => {
      write.mockRejectedValueOnce(new Error('boom'));

      await expect(composable.toggle(ADDRESS, ['eth'])).rejects.toThrow('boom');

      expect((await composable.toggle(OTHER_ADDRESS, ['optimism'])).success).toBe(true);
      expect(writtenPayload()).toEqual({ optimism: [OTHER_ADDRESS] });
    });

    it('should keep writing after one of them is rejected', async () => {
      write.mockResolvedValueOnce({ message: 'nope', success: false });
      const release = writeThroughRepo();
      release();

      const [rejected] = await Promise.all([
        composable.toggle(ADDRESS, ['eth']),
        composable.toggle(OTHER_ADDRESS, ['optimism']),
      ]);

      expect(rejected.success).toBe(false);
      expect(writtenPayload()).toEqual({ optimism: [OTHER_ADDRESS] });
    });
  });

  describe('unskipAddress, on payloads the composable never hands it', () => {
    it('should leave a chain with no rule of its own untouched', () => {
      expect(unskipAddress({ eth: [OTHER_ADDRESS] }, ADDRESS, ['optimism']))
        .toEqual({ eth: [OTHER_ADDRESS] });
    });

    it('should keep the empty array of a chain switched off whole, never emptying it further', () => {
      expect(unskipAddress({ eth: [] }, ADDRESS, ['eth'])).toEqual({ eth: [] });
    });

    it('should leave a rule that does not name this address', () => {
      expect(unskipAddress({ eth: [OTHER_ADDRESS] }, ADDRESS, ['eth']))
        .toEqual({ eth: [OTHER_ADDRESS] });
    });
  });

  describe('skipAddress, on payloads the composable never hands it', () => {
    it('should not narrow a chain that is switched off whole', () => {
      expect(skipAddress({ eth: [] }, ADDRESS, ['eth'])).toEqual({ eth: [] });
    });

    it('should not add an address the rule already names', () => {
      expect(skipAddress({ eth: [ADDRESS] }, ADDRESS, ['eth'])).toEqual({ eth: [ADDRESS] });
    });

    it('should replace an entry that differs only by case, which the backend would never match', () => {
      expect(skipAddress({ eth: [ADDRESS.toLowerCase()] }, ADDRESS, ['eth'])).toEqual({ eth: [ADDRESS] });
    });
  });
});
