import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, nextTick } from 'vue';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { createNewBlockchainAccount } from '@/modules/accounts/blockchain/new-account-state';
import AccountForm from '@/modules/accounts/management/AccountForm.vue';
import { useSupportedChainsStore } from '@/modules/core/common/use-supported-chains-store';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';

const apiKeys = vi.hoisted(() => new Map<string, string>());

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: vi.fn(() => ({ getApiKey: (name: string): string => apiKeys.get(name) ?? '' })),
}));

const ethereum: EvmChainInfo = {
  evmChainName: 'ethereum',
  id: Blockchain.ETH,
  image: '',
  name: 'Ethereum',
  nativeToken: 'ETH',
  type: 'evm',
};

const optimism: EvmChainInfo = {
  evmChainName: 'optimism',
  id: 'optimism',
  image: '',
  name: 'Optimism',
  nativeToken: 'ETH',
  type: 'evm',
};

/**
 * `AccountForm.validate()` falls back to `true` when the selected child does not expose a
 * `validate` method, so a child that stops exposing it under that exact name sends every account
 * save through unvalidated, with no error and nothing but a debug log. Typecheck does not catch it
 * either. These tests pin the delegation for all four branches: each asserts the child's `false`
 * comes back out, which is precisely what the fail-open path cannot produce.
 */

const inputValidate = vi.fn<() => Promise<boolean>>();

/** The leaf inputs are stubbed down to the one thing the intermediate forms call on them. */
function inputStub(name: string): Record<string, unknown> {
  return {
    methods: { validate: inputValidate },
    name,
    template: '<div />',
  };
}

function createWrapper(modelValue: AccountManageState): VueWrapper<InstanceType<typeof AccountForm>> {
  return mount(AccountForm, {
    global: {
      stubs: {
        AccountDataInput: true,
        AccountSelector: {
          emits: ['update:chain'],
          name: 'AccountSelector',
          props: ['chain', 'chainIds', 'editMode'],
          template: '<div />',
        },
        AddressInput: inputStub('AddressInput'),
        BtcAddressInput: inputStub('BtcAddressInput'),
        Eth2Input: inputStub('Eth2Input'),
        ModuleActivator: true,
      },
    },
    props: {
      chainIds: [],
      errorMessages: {},
      loading: false,
      modelValue,
    },
  });
}

function xpubAccount(): AccountManageState {
  return {
    chain: Blockchain.BTC,
    data: {
      tags: null,
      xpub: {
        derivationPath: '',
        xpub: '',
        xpubType: XpubKeyType.ZPUB,
      },
    },
    mode: 'edit',
    type: 'xpub',
  };
}

function validatorAccount(): AccountManageState {
  return {
    chain: Blockchain.ETH2,
    data: {},
    mode: 'edit',
    type: 'validator',
  };
}

function groupAccount(): AccountManageState {
  return {
    category: 'evm',
    chain: undefined,
    data: {
      address: '0x9531C059098e3d194fF87FebB587aB07B30B1306',
      tags: null,
    },
    mode: 'edit',
    type: 'group',
  };
}

describe('modules/accounts/management/AccountForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountForm>>;

  beforeEach(() => {
    setActivePinia(createPinia());
    inputValidate.mockReset();
    inputValidate.mockResolvedValue(false);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it.each([
    ['a blockchain account', createNewBlockchainAccount],
    ['an account group', groupAccount],
    ['an xpub', xpubAccount],
    ['a validator', validatorAccount],
  ])('should report the rejection raised by the form for %s', async (_label, model) => {
    wrapper = createWrapper(model());

    expect(await wrapper.vm.validate()).toBe(false);
    expect(inputValidate).toHaveBeenCalledTimes(1);
  });

  /*
   * Choosing a chain does not edit the state, it replaces it: each chain implies a different kind
   * of account, with a different shape of `data` and a different child form to edit it in. What is
   * pinned here is that one choice produces one coherent state, because the shapes are a
   * discriminated union and a `chain` written onto the wrong variant type-checks by accident.
   */
  describe('choosing a chain', () => {
    function selector(): VueWrapper<ComponentPublicInstance<Record<string, unknown>>> {
      return wrapper.findComponent<ComponentPublicInstance<Record<string, unknown>>>({ name: 'AccountSelector' });
    }

    function lastModel(): AccountManageState {
      const last = wrapper.emitted<[AccountManageState]>('update:modelValue')?.at(-1);
      assert(last);
      return last[0];
    }

    async function choose(chain: string): Promise<void> {
      selector().vm.$emit('update:chain', chain);
      await nextTick();
    }

    it('should turn the state into a validator when eth2 is chosen', async () => {
      wrapper = createWrapper(createNewBlockchainAccount());

      await choose(Blockchain.ETH2);

      // A validator is keyed by its index or public key, so none of the address account's data
      // survives the switch.
      expect(lastModel()).toStrictEqual({
        chain: Blockchain.ETH2,
        data: {},
        mode: 'add',
        type: 'validator',
      });
    });

    it('should turn the state back into an address account off eth2', async () => {
      wrapper = createWrapper({ chain: Blockchain.ETH2, data: {}, mode: 'add', type: 'validator' });

      await choose(Blockchain.BTC);

      const model = lastModel();
      expect(model.type).toBe('account');
      expect(model.chain).toBe(Blockchain.BTC);
    });

    it('should carry the addresses already typed across a chain change', async () => {
      const started = createNewBlockchainAccount();
      started.data = [{ address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null }];
      wrapper = createWrapper(started);

      await choose(Blockchain.BTC);

      // Only the chain was answered, so what the user had already typed is still the answer to a
      // different question.
      expect(lastModel().data).toStrictEqual(started.data);
    });

    it('should leave an account being edited on its own chain', async () => {
      // An edit is anchored to an account that already exists, so its chain is not up for choosing.
      // The selector is disabled for it, which is the only reason this was not reachable before:
      // the guard sat on the rebuild while the chain was written before it ran.
      wrapper = createWrapper(xpubAccount());

      await choose(Blockchain.ETH2);

      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });

    it('should never leave the chain and the account type disagreeing', async () => {
      wrapper = createWrapper(createNewBlockchainAccount());

      await choose(Blockchain.ETH2);

      // Every emitted state, not only the last: the field used to be written onto the previous
      // kind and corrected a beat later, so the pairing held at rest and not in between.
      const states = wrapper.emitted<[AccountManageState]>('update:modelValue') ?? [];
      expect(states.length).toBeGreaterThan(0);
      for (const [state] of states)
        expect(state.type === 'validator').toBe(state.chain === Blockchain.ETH2);
    });

    it('should render the validator form for a validator seeded without a chain being chosen', () => {
      wrapper = createWrapper({ chain: Blockchain.ETH2, data: {}, mode: 'add', type: 'validator' });

      expect(wrapper.findComponent({ name: 'Eth2Input' }).exists()).toBe(true);
      expect(wrapper.findComponent({ name: 'AddressInput' }).exists()).toBe(false);
    });

    it('should not report an edit the form never made', () => {
      wrapper = createWrapper(createNewBlockchainAccount());

      // Opening on a chain is not choosing one. The rebuild used to run on mount as well, so the
      // form answered a question nobody had asked yet.
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });
  });

  /*
   * The warning names the key the history query is actually missing. On a chain that queries
   * Etherscan first, an Etherscan key is what the query needs; Blockscout is a fallback there, and
   * the backend skips it without a key, so its absence must not be reported as a requirement.
   */
  describe('indexer api key warning', () => {
    const ethereumAccount = (): AccountManageState => ({
      chain: Blockchain.ETH,
      data: [{ address: '', tags: null }],
      mode: 'add',
      type: 'account',
    });

    function mountOnEthereum(): void {
      useSupportedChainsStore().supportedChains = [ethereum];
      wrapper = createWrapper(ethereumAccount());
      updateGeneralSettings({ defaultEvmIndexerOrder: [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT] });
    }

    beforeEach(() => {
      apiKeys.clear();
    });

    it('should not ask for a blockscout key when etherscan leads and has a key', async () => {
      apiKeys.set('etherscan', 'etherscan-key');
      mountOnEthereum();
      await nextTick();

      expect(wrapper.text()).not.toContain('external_services.blockscout.api_key_message');
      expect(wrapper.text()).not.toContain('external_services.etherscan.api_key_message');
    });

    it('should ask for an etherscan key when etherscan leads without one', async () => {
      mountOnEthereum();
      await nextTick();

      expect(wrapper.text()).toContain('external_services.etherscan.api_key_message');
    });

    /*
     * Optimism, Base and Gnosis lead with Blockscout, and Etherscan's free tier does not serve
     * them, so there a missing Blockscout key is what stops the query, Etherscan key or not.
     */
    function mountOnOptimism(): void {
      useSupportedChainsStore().supportedChains = [optimism];
      wrapper = createWrapper({
        chain: 'optimism',
        data: [{ address: '', tags: null }],
        mode: 'add',
        type: 'account',
      });
      updateGeneralSettings({
        defaultEvmIndexerOrder: [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT],
        evmIndexersOrder: { optimism: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ROUTESCAN, EvmIndexer.ETHERSCAN] },
      });
    }

    it('should ask for a blockscout key naming the chain when blockscout leads without one', async () => {
      apiKeys.set('etherscan', 'etherscan-key');
      mountOnOptimism();
      await nextTick();

      expect(wrapper.text()).toContain('external_services.blockscout.api_key_message::Optimism');
      expect(wrapper.text()).not.toContain('external_services.etherscan.api_key_message');
    });

    it('should not ask for a blockscout key when blockscout leads and has one', async () => {
      apiKeys.set('blockscout', 'blockscout-key');
      mountOnOptimism();
      await nextTick();

      expect(wrapper.text()).not.toContain('external_services.blockscout.api_key_message');
    });
  });
});
