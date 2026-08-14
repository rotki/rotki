import type { Ref } from 'vue';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const suggestions = ref<string[]>([]);
const getAddressName = vi.fn();

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: vi.fn().mockReturnValue({
    getAddressName: vi.fn().mockImplementation((...args: unknown[]) => getAddressName(...args)),
    useAddressesWithoutNames: vi.fn().mockImplementation(() => suggestions),
  }),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn().mockReturnValue({
    addresses: computed<Record<string, string[]>>(() => ({ eth: ['0xabc'] })),
  }),
}));

const { useAddressSuggestions } = await import('@/modules/accounts/address-book/use-address-suggestions');

interface Selection {
  address: Ref<string>;
  cleared: () => number;
}

function mountWith(chain: string | null, address: string): { selection: Selection; unmount: () => void } {
  const selected = ref<string>(address);
  const clear = vi.fn().mockImplementation(() => set(selected, ''));

  const { wrapper } = withSetup(() => useAddressSuggestions(() => chain, {
    clear,
    selected: () => get(selected),
  }));

  return {
    selection: {
      address: selected,
      cleared: (): number => clear.mock.calls.length,
    },
    unmount: (): void => wrapper.unmount(),
  };
}

describe('modules/accounts/address-book/useAddressSuggestions', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(suggestions, ['0xabc', '0xdef']);
    getAddressName.mockClear();
  });

  it('should clear an address that stops being offered for the chosen chain', async () => {
    const { selection, unmount } = mountWith('eth', '0xabc');

    set(suggestions, ['0xdef']);
    await nextTick();

    expect(selection.cleared()).toBe(1);
    expect(get(selection.address)).toBe('');
    unmount();
  });

  it('should keep an address the user typed themselves', async () => {
    // It was never offered, so it dropping out of a list it was never on means nothing.
    const { selection, unmount } = mountWith('eth', '0x999');

    set(suggestions, ['0xdef']);
    await nextTick();

    expect(selection.cleared()).toBe(0);
    expect(get(selection.address)).toBe('0x999');
    unmount();
  });

  it('should keep the address while no chain is chosen', async () => {
    const { selection, unmount } = mountWith(null, '0xabc');

    set(suggestions, ['0xdef']);
    await nextTick();

    expect(selection.cleared()).toBe(0);
    unmount();
  });

  it('should resolve the tracked addresses so the unnamed ones can be offered', () => {
    const { unmount } = mountWith('eth', '');

    expect(getAddressName).toHaveBeenCalledWith('0xabc', 'eth');
    unmount();
  });
});
