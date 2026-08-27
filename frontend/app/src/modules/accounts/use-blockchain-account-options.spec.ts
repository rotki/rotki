import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBlockchainAccountOptions } from '@/modules/accounts/use-blockchain-account-options';

interface TestAccount {
  data: { type: string; address?: string; xpub?: string };
  chains: string[];
  label?: string;
  tags?: string[];
}

const accounts = ref<TestAccount[]>([]);
const names: Record<string, string> = {};

vi.mock('@/modules/balances/blockchain/use-blockchain-account-data', () => ({
  useBlockchainAccountData: (): { getAccountsByCategory: () => typeof accounts } => ({
    getAccountsByCategory: (): typeof accounts => accounts,
  }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): { getAddressName: (address: string) => string | undefined } => ({
    getAddressName: (address: string): string | undefined => names[address],
  }),
}));

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): { scrambleAddress: (address: string) => string } => ({
    scrambleAddress: (address: string): string => address,
  }),
}));

function addressAccount(address: string, extras: Partial<TestAccount> = {}): TestAccount {
  return { chains: ['eth'], data: { address, type: 'address' }, ...extras };
}

describe('useBlockchainAccountOptions', () => {
  beforeEach(() => {
    accounts.value = [];
    for (const key of Object.keys(names))
      delete names[key];
  });

  it('should show a named account as its name with the address as the caption', () => {
    const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
    names[address] = 'vitalik.eth';
    accounts.value = [addressAccount(address)];

    const { resolveCaption, resolveLabel, suggest } = useBlockchainAccountOptions('evm');
    expect(suggest()).toStrictEqual([address]);
    expect(resolveLabel(address)).toBe('vitalik.eth');
    expect(resolveCaption(address)).toBe('0x5A0b...9c4c');
  });

  it('should show an unnamed account as its shortened address and no caption', () => {
    const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
    accounts.value = [addressAccount(address)];

    const { resolveCaption, resolveLabel } = useBlockchainAccountOptions('evm');
    expect(resolveLabel(address)).toBe('0x5A0b...9c4c');
    expect(resolveCaption(address)).toBeUndefined();
  });

  it('should show an unlabelled xpub as its shortened value alone, rather than render it twice as both label and caption', () => {
    const xpub = 'xpub68V4ZQQ62mea7ZUKn2urQuIpsGtRSfRkACCWo4KKR8dQ';
    accounts.value = [{ chains: ['btc'], data: { type: 'xpub', xpub } }];

    const { resolveCaption, resolveLabel, suggest } = useBlockchainAccountOptions('btc');
    expect(suggest()).toStrictEqual([xpub]);
    expect(resolveLabel(xpub)).toBe('xpub68V4...R8dQ');
    expect(resolveCaption(xpub)).toBeUndefined();
  });

  it('should name an xpub by its own label rather than the address book', () => {
    const xpub = 'xpub68V4ZQQ62mea7ZUKn2urQuIpsGtRSfRkACCWo4KKR8dQ';
    accounts.value = [{ chains: ['btc'], data: { type: 'xpub', xpub }, label: 'Cold storage' }];

    const { resolveCaption, resolveLabel } = useBlockchainAccountOptions('btc');
    expect(resolveLabel(xpub)).toBe('Cold storage');
    expect(resolveCaption(xpub)).toBe('xpub68V4...R8dQ');
  });

  it('should fall back to the label a non-evm account was tracked under, which rarely has an alias name to resolve', () => {
    const address = '13UVJyLnbVp9RBZYFwFGyDvVd1y27Tt8tkntv6Q7JVPhFsTB';
    accounts.value = [{ chains: ['polkadot'], data: { address, type: 'address' }, label: 'Staking' }];

    const { resolveLabel, suggest } = useBlockchainAccountOptions('substrate');
    expect(suggest()).toStrictEqual([address]);
    expect(resolveLabel(address)).toBe('Staking');
  });

  it('should offer an account once when it is tracked on several chains', () => {
    const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
    accounts.value = [addressAccount(address), addressAccount(address, { chains: ['optimism'] })];

    expect(useBlockchainAccountOptions('evm').suggest()).toStrictEqual([address]);
  });

  it('should find an account by its address, name or tags', () => {
    const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';
    names[address] = 'vitalik.eth';
    accounts.value = [addressAccount(address, { tags: ['Public', 'Donations'] })];

    const keywords = useBlockchainAccountOptions('evm').resolveKeywords(address);
    // Lowercased, because the list's search box lowercases what is typed into it.
    expect(keywords).toBe(`${address.toLowerCase()} vitalik.eth public donations`);
  });
});
