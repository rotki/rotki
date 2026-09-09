import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import QueriedAddressDialog from '@/modules/accounts/QueriedAddressDialog.vue';
import { Module } from '@/modules/core/common/modules';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

const { addQueriedAddress, deleteQueriedAddress, getAccounts, getAddresses } = vi.hoisted(() => ({
  addQueriedAddress: vi.fn(async () => {}),
  deleteQueriedAddress: vi.fn(async () => {}),
  getAccounts: vi.fn<(chain: string) => BlockchainAccount[]>(() => []),
  getAddresses: vi.fn<(chain: string) => string[]>(() => []),
}));

vi.mock('@/modules/accounts/use-queried-address-operations', () => ({
  useQueriedAddressOperations: (): Record<string, unknown> => ({ addQueriedAddress, deleteQueriedAddress }),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: (): Record<string, unknown> => ({ getAccounts }),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: (): Record<string, unknown> => ({ getAddresses }),
}));

const ADDRESSES = [
  '0x9531C059098e3d194fF87FebB587aB07B30B1306',
  '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',
];

/** Stands in for the account picker, exposing what it was offered and letting a test pick one. */
const AccountSelectorStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue', 'source', 'field'],
  template: '<div />',
});

function account(address: string): BlockchainAccount<AddressData> {
  return {
    chain: Blockchain.ETH,
    data: { address, type: 'address' },
    nativeAsset: 'ETH',
    tags: ['mine'],
  };
}

function createWrapper(module: Module = Module.ETH2): VueWrapper<any> {
  return mount(QueriedAddressDialog, {
    global: {
      stubs: {
        AppImage: true,
        BlockchainAccountSelector: AccountSelectorStub,
        LabeledAddressDisplay: { props: ['account'], template: '<div class="address">{{ account.data.address }}</div>' },
        RuiDialog: { template: '<div><slot /></div>' },
        RuiTooltip: { template: '<div><slot name="activator" /></div>' },
        TagDisplay: true,
      },
    },
    props: { module },
  });
}

function selector(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(AccountSelectorStub);
}

/** The addresses already queried for this module, as the list renders them. */
function listed(wrapper: VueWrapper<any>): string[] {
  return wrapper.findAll('.address').map(node => node.text());
}

/** The add button, told apart from the close and remove buttons by its own id. */
function addButton(wrapper: VueWrapper<any>): VueWrapper<any> {
  const found = wrapper
    .findAllComponents({ name: 'RuiButton' })
    .find(button => button.attributes('data-testid') === 'queried-address-add');
  assert(found);
  return found;
}

async function pick(wrapper: VueWrapper<any>, address: string): Promise<void> {
  selector(wrapper).vm.$emit('update:modelValue', [account(address)]);
  await nextTick();
}

describe('queriedAddressDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    getAccounts.mockImplementation(() => ADDRESSES.map(address => account(address)));
    getAddresses.mockImplementation(() => ADDRESSES);
    set(storeToRefs(useSessionMetadataStore()).queriedAddresses, {});
  });

  function queried(addresses: Record<string, string[]>): void {
    set(storeToRefs(useSessionMetadataStore()).queriedAddresses, addresses);
  }

  /**
   * The module identifier is snake_case while the map is keyed in camelCase, so the lookup has to
   * transform it or every module reads as having no addresses at all.
   */
  describe('the addresses already queried', () => {
    it('should list the ones stored under the module', () => {
      queried({ eth2: [ADDRESSES[0]] });

      expect(listed(createWrapper(Module.ETH2))).toEqual([ADDRESSES[0]]);
    });

    it('should find a multi-word module under its camelCase key', () => {
      queried({ makerdaoVaults: [ADDRESSES[0]] });

      expect(listed(createWrapper(Module.MAKERDAO_VAULTS))).toEqual([ADDRESSES[0]]);
    });

    it('should list none for a module with no addresses of its own', () => {
      queried({ eth2: [ADDRESSES[0]] });

      expect(listed(createWrapper(Module.NFTS))).toEqual([]);
    });

    it('should say so when the module queries every address', () => {
      const wrapper = createWrapper();

      expect(wrapper.text()).toContain('queried_address_dialog.all_address_queried');
    });
  });

  /** Offering an address that is already queried would only produce a duplicate. */
  describe('the addresses on offer', () => {
    it('should leave out the ones already queried', () => {
      queried({ eth2: [ADDRESSES[0]] });

      expect(selector(createWrapper()).props('source').usableAddresses).toEqual([ADDRESSES[1]]);
    });

    it('should offer every address while none are queried', () => {
      expect(selector(createWrapper()).props('source').usableAddresses).toEqual(ADDRESSES);
    });
  });

  describe('adding an address', () => {
    it('should refuse to add while nothing is picked', () => {
      expect(addButton(createWrapper()).props('disabled')).toBe(true);
    });

    it('should offer the add once an account is picked', async () => {
      const wrapper = createWrapper();

      await pick(wrapper, ADDRESSES[0]);

      expect(addButton(wrapper).props('disabled')).toBe(false);
    });

    it('should add the picked address for this module', async () => {
      const wrapper = createWrapper(Module.NFTS);
      await pick(wrapper, ADDRESSES[0]);

      await addButton(wrapper).trigger('click');

      expect(addQueriedAddress).toHaveBeenCalledWith({ address: ADDRESSES[0], module: Module.NFTS });
    });

    it('should clear the picker once it has been added', async () => {
      const wrapper = createWrapper();
      await pick(wrapper, ADDRESSES[0]);

      await addButton(wrapper).trigger('click');
      await flushPromises();

      expect(selector(wrapper).props('modelValue')).toEqual([]);
    });
  });

  it('should remove an address from the module', async () => {
    queried({ eth2: [ADDRESSES[0]] });
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=queried-address-remove]').trigger('click');

    expect(deleteQueriedAddress).toHaveBeenCalledWith({ address: ADDRESSES[0], module: Module.ETH2 });
  });

  it('should report being closed', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=queried-address-close]').trigger('click');

    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
