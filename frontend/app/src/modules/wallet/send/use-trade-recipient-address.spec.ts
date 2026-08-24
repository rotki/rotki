import type { Ref } from 'vue';
import type { AddressBookEntry } from '@/modules/accounts/address-book/eth-names';
import type { Collection } from '@/modules/core/common/collection';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeRecipientAddress } from '@/modules/wallet/send/use-trade-recipient-address';

/**
 * The seam: what a typed search turns into, and which of those the recipient can end up being.
 * Three sources feed the suggestions (the private address book, the tracked accounts and ENS), the
 * connected account is never among them, and only a real address is ever taken as the recipient.
 */

const ALICE = '0x9531C059098e3d194fF87FebB587aB07B30B1306';
const BOB = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12';
const CONNECTED = '0x1234567890123456789012345678901234567890';

const getAddressBook = vi.fn<() => Promise<Collection<AddressBookEntry>>>();
const fetchEnsNames = vi.fn<() => Promise<void>>();
const resolveEnsToAddress = vi.fn<(name: string) => Promise<string | null>>();

vi.mock('@/modules/accounts/address-book/use-address-book-operations', () => ({
  useAddressBookOperations: (): { getAddressBook: typeof getAddressBook } => ({ getAddressBook }),
}));

vi.mock('@/modules/accounts/address-book/use-ens-operations', () => ({
  useEnsOperations: (): {
    fetchEnsNames: typeof fetchEnsNames;
    resolveEnsToAddress: typeof resolveEnsToAddress;
  } => ({ fetchEnsNames, resolveEnsToAddress }),
}));

const addresses = ref<Record<string, string[]>>({});

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: (): { addresses: typeof addresses } => ({ addresses }),
}));

const connectedAddress = ref<string>('');

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: (): { connectedAddress: typeof connectedAddress } => ({ connectedAddress }),
}));

function bookEntries(...entries: { address: string; name: string }[]): Collection<AddressBookEntry> {
  return {
    data: entries.map(entry => ({ address: entry.address, blockchain: null, name: entry.name })),
    found: entries.length,
    limit: 10,
    total: entries.length,
    totalValue: undefined,
  };
}

describe('useTradeRecipientAddress', () => {
  let model: Ref<string>;
  let recipient: ReturnType<typeof useTradeRecipientAddress>;

  beforeEach(() => {
    vi.clearAllMocks();
    set(addresses, {});
    set(connectedAddress, '');
    getAddressBook.mockResolvedValue(bookEntries());
    resolveEnsToAddress.mockResolvedValue(null);
    fetchEnsNames.mockResolvedValue();
    model = ref<string>('');
    recipient = useTradeRecipientAddress(model);
  });

  describe('valid', () => {
    it('should accept an empty recipient and a real address, and nothing else', () => {
      expect(get(recipient.valid)).toBe(true);

      set(model, ALICE);
      expect(get(recipient.valid)).toBe(true);

      set(model, 'not-an-address');
      expect(get(recipient.valid)).toBe(false);
    });
  });

  describe('searchAddresses', () => {
    it('should offer the address book entries it found', async () => {
      getAddressBook.mockResolvedValue(bookEntries({ address: ALICE, name: 'Alice' }));

      await recipient.searchAddresses('ali');

      expect(getAddressBook).toHaveBeenCalledWith('private', { limit: 10, nameSubstring: 'ali', offset: 0 });
      expect(get(recipient.directOptions)).toEqual([{ address: ALICE, name: 'Alice' }]);
    });

    it('should skip an address book entry that is not an address', async () => {
      getAddressBook.mockResolvedValue(bookEntries({ address: 'nonsense', name: 'Broken' }));

      await recipient.searchAddresses('bro');

      expect(get(recipient.directOptions)).toEqual([]);
    });

    it('should offer the tracked accounts that match', async () => {
      set(addresses, { eth: [ALICE, BOB], optimism: [ALICE] });

      await recipient.searchAddresses(ALICE.slice(0, 6));

      expect(get(recipient.directOptions)).toEqual([{ address: ALICE }]);
    });

    it('should resolve an ens name and offer it under that name', async () => {
      resolveEnsToAddress.mockResolvedValue(ALICE);

      await recipient.searchAddresses('alice.eth');

      expect(resolveEnsToAddress).toHaveBeenCalledWith('alice.eth');
      expect(get(recipient.directOptions)).toEqual([{ address: ALICE, name: 'alice.eth' }]);
      expect(get(recipient.resolvingEns)).toBe(false);
    });

    it('should offer nothing extra for an ens name that resolves to nobody', async () => {
      await recipient.searchAddresses('nobody.eth');

      expect(get(recipient.directOptions)).toEqual([]);
      expect(get(recipient.resolvingEns)).toBe(false);
    });

    it('should offer a pasted address as-is and look its name up in the background', async () => {
      await recipient.searchAddresses(ALICE);

      expect(fetchEnsNames).toHaveBeenCalledWith([{ address: ALICE, blockchain: null }]);
      expect(get(recipient.directOptions)).toEqual([{ address: ALICE }]);
    });

    it('should offer an address found twice only once', async () => {
      getAddressBook.mockResolvedValue(bookEntries({ address: ALICE, name: 'Alice' }));
      set(addresses, { eth: [ALICE] });

      await recipient.searchAddresses(ALICE);

      // The later, nameless entry wins the deduplication, so pasting an address you have in the
      // address book shows it without its name. Pre-existing, kept here as the record of it.
      expect(get(recipient.directOptions)).toEqual([{ address: ALICE }]);
    });

    it('should never offer the connected account', async () => {
      set(connectedAddress, CONNECTED);
      getAddressBook.mockResolvedValue(bookEntries({ address: CONNECTED, name: 'Me' }));
      set(addresses, { eth: [CONNECTED, ALICE] });

      await recipient.searchAddresses('');

      expect(get(recipient.directOptions)).toEqual([{ address: ALICE }]);
    });
  });

  describe('trackedAddresses', () => {
    it('should list every tracked address once, minus the connected one', () => {
      set(addresses, { eth: [ALICE, BOB, CONNECTED], optimism: [ALICE], bitcoin: ['bc1qsomething'] });
      set(connectedAddress, CONNECTED);

      expect(get(recipient.trackedAddresses)).toEqual([ALICE, BOB]);
    });
  });

  describe('select', () => {
    it('should take the address and put both menus away', () => {
      set(recipient.modelOpenOptionsDialog, true);
      set(recipient.modelSearchValue, 'ali');

      recipient.select(ALICE);

      expect(get(model)).toBe(ALICE);
      expect(get(recipient.modelOpenOptionsDialog)).toBe(false);
      expect(get(recipient.modelOpenSuggestionsMenu)).toBe(false);
      expect(get(recipient.modelSearchValue)).toBe('');
    });

    it('should refuse the connected account', () => {
      set(connectedAddress, CONNECTED);

      recipient.select(CONNECTED);

      expect(get(model)).toBe('');
    });
  });

  describe('applySearchInput', () => {
    it('should take a typed address as the recipient', () => {
      set(recipient.modelSearchValue, ALICE);

      recipient.applySearchInput();

      expect(get(model)).toBe(ALICE);
    });

    it('should leave a half-typed address alone', () => {
      set(recipient.modelSearchValue, '0x123');

      recipient.applySearchInput();

      expect(get(model)).toBe('');
      expect(get(recipient.modelSearchValue)).toBe('0x123');
    });
  });

  describe('handleFocusChange', () => {
    it('should open the suggestions while the input has focus', () => {
      recipient.handleFocusChange(true);

      expect(get(recipient.modelOpenSuggestionsMenu)).toBe(true);
    });

    it('should keep a typed address when focus leaves', () => {
      set(recipient.modelSearchValue, ALICE);

      recipient.handleFocusChange(false);

      expect(get(model)).toBe(ALICE);
      expect(get(recipient.modelOpenSuggestionsMenu)).toBe(false);
    });

    it('should throw away anything else when focus leaves', () => {
      set(recipient.modelSearchValue, 'half-typed');

      recipient.handleFocusChange(false);

      expect(get(model)).toBe('');
      expect(get(recipient.modelSearchValue)).toBe('');
    });
  });

  it('should drop the recipient when it becomes the connected account', async () => {
    set(model, CONNECTED);

    set(connectedAddress, CONNECTED);
    await nextTick();

    expect(get(model)).toBe('');
  });

  it('should keep a recipient that is not the connected account', async () => {
    set(model, ALICE);

    set(connectedAddress, CONNECTED);
    await nextTick();

    expect(get(model)).toBe(ALICE);
  });

  describe('the address book dialog', () => {
    it('should read the address book while the dialog is open', async () => {
      vi.useFakeTimers();
      getAddressBook.mockResolvedValue(bookEntries({ address: ALICE, name: 'Alice' }));

      set(recipient.modelOpenOptionsDialog, true);
      set(recipient.modelAddressBookSearch, 'ali');
      await vi.advanceTimersByTimeAsync(250);

      expect(getAddressBook).toHaveBeenCalledWith('private', { limit: 10, nameSubstring: 'ali', offset: 0 });
      expect(get(recipient.filteredAddressBookOptions)).toEqual([ALICE]);
      vi.useRealTimers();
    });

    it('should forget the search when the dialog closes', async () => {
      set(recipient.modelOpenOptionsDialog, true);
      set(recipient.modelAddressBookSearch, 'ali');
      await nextTick();

      set(recipient.modelOpenOptionsDialog, false);
      await nextTick();

      expect(get(recipient.modelAddressBookSearch)).toBe('');
    });
  });
});
