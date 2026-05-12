import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ChainAccountMultiSelect from '@/modules/accounts/ChainAccountMultiSelect.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';

const ensByAddress = new Map<string, string>();

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): { getAddressName: (address: string) => string | undefined } => ({
    getAddressName: (address: string): string | undefined => ensByAddress.get(address),
  }),
}));

function addressAccount(chain: string, address: string, label?: string): BlockchainAccount {
  return {
    chain,
    data: { type: 'address', address },
    label,
    nativeAsset: 'ETH',
  };
}

function validatorAccount(chain: string, publicKey: string, index: number, label?: string): BlockchainAccount {
  return {
    chain,
    data: { type: 'validator', publicKey, index, status: 'active' },
    label,
    nativeAsset: 'ETH',
  };
}

interface ExposedOption {
  id: string;
  kind: 'address' | 'validator';
  validatorIndex?: number;
  searchText: string;
}

describe('chain-account-multi-select', () => {
  let wrapper: VueWrapper<InstanceType<typeof ChainAccountMultiSelect>>;

  function createWrapper(props: { chain: string; modelValue?: string[] }): VueWrapper<InstanceType<typeof ChainAccountMultiSelect>> {
    const pinia = createPinia();
    setActivePinia(pinia);

    return mount(ChainAccountMultiSelect, {
      props: {
        'chain': props.chain,
        'modelValue': props.modelValue ?? [],
        'onUpdate:modelValue': (): void => {},
      },
      pinia,
      provide: libraryDefaults,
    });
  }

  function exposed(): InstanceType<typeof ChainAccountMultiSelect> {
    return wrapper.vm;
  }

  beforeEach(() => {
    ensByAddress.clear();
  });

  it('should build one option per unique address account', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useBlockchainAccountsStore();
    store.accounts = {
      eth: [
        addressAccount('eth', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'),
        addressAccount('eth', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'),
        addressAccount('eth', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c'), // duplicate — should be ignored
      ],
    };

    wrapper = mount(ChainAccountMultiSelect, {
      props: { 'chain': 'eth', 'modelValue': [], 'onUpdate:modelValue': (): void => {} },
      pinia,
      provide: libraryDefaults,
    });
    await flushPromises();

    expect(exposed().options.map(o => o.id)).toEqual([
      '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
      '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',
    ]);
    expect(exposed().options.every(o => o.kind === 'address')).toBe(true);
  });

  it('should build validator options with publicKey ids and surface the index', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useBlockchainAccountsStore();
    store.accounts = {
      eth2: [
        validatorAccount('eth2', '0xpubkey1', 42),
        validatorAccount('eth2', '0xpubkey2', 7),
      ],
    };

    wrapper = mount(ChainAccountMultiSelect, {
      props: { 'chain': 'eth2', 'modelValue': [], 'onUpdate:modelValue': (): void => {} },
      pinia,
      provide: libraryDefaults,
    });
    await flushPromises();

    const opts = exposed().options;
    expect(opts).toHaveLength(2);
    expect(opts.every(o => o.kind === 'validator')).toBe(true);
    const pub1 = opts.find(o => o.id === '0xpubkey1');
    expect(pub1?.validatorIndex).toBe(42);
  });

  it('should return an empty option list for an unknown chain', async () => {
    wrapper = createWrapper({ chain: 'sepolia' });
    await flushPromises();

    expect(exposed().options).toEqual([]);
  });

  it('should match against the address substring', () => {
    wrapper = createWrapper({ chain: 'eth' });
    const option: ExposedOption = {
      id: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
      kind: 'address',
      searchText: '0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c'.toLowerCase(),
    };

    expect(exposed().filterOption(option, '5A0b')).toBe(true);
    expect(exposed().filterOption(option, '0x5a0b')).toBe(true);
    expect(exposed().filterOption(option, 'deadbeef')).toBe(false);
  });

  it('should match against the user label and ENS name', () => {
    wrapper = createWrapper({ chain: 'eth' });
    const option: ExposedOption = {
      id: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
      kind: 'address',
      searchText: '0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c my hot wallet vitalik.eth'.toLowerCase(),
    };

    expect(exposed().filterOption(option, 'hot wallet')).toBe(true);
    expect(exposed().filterOption(option, 'vitalik.eth')).toBe(true);
    expect(exposed().filterOption(option, 'Vitalik')).toBe(true);
    expect(exposed().filterOption(option, 'cold')).toBe(false);
  });

  it('should match validators by their numeric index', () => {
    wrapper = createWrapper({ chain: 'eth2' });
    const option: ExposedOption = {
      id: '0xpubkey1',
      kind: 'validator',
      validatorIndex: 42,
      searchText: '0xpubkey1 42'.toLowerCase(),
    };

    expect(exposed().filterOption(option, '42')).toBe(true);
    expect(exposed().filterOption(option, '99')).toBe(false);
  });

  it('should pass an empty query', () => {
    wrapper = createWrapper({ chain: 'eth' });
    const option: ExposedOption = { id: 'x', kind: 'address', searchText: 'x' };
    expect(exposed().filterOption(option, '')).toBe(true);
    expect(exposed().filterOption(option, '   ')).toBe(true);
  });

  it('should include ENS in the option searchText when available', async () => {
    ensByAddress.set('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', 'vitalik.eth');

    const pinia = createPinia();
    setActivePinia(pinia);
    const store = useBlockchainAccountsStore();
    store.accounts = {
      eth: [addressAccount('eth', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', 'Main')],
    };

    wrapper = mount(ChainAccountMultiSelect, {
      props: { 'chain': 'eth', 'modelValue': [], 'onUpdate:modelValue': (): void => {} },
      pinia,
      provide: libraryDefaults,
    });
    await flushPromises();

    const option = exposed().options[0];
    expect(option.searchText).toContain('vitalik.eth');
    expect(option.searchText).toContain('main');
    expect(exposed().filterOption(option, 'vitalik')).toBe(true);
    expect(exposed().filterOption(option, 'main')).toBe(true);
  });
});
