import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, nextTick } from 'vue';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { type AccountManageState, createNewBlockchainAccount } from '@/modules/accounts/blockchain/use-account-manage';
import AccountForm from '@/modules/accounts/management/AccountForm.vue';

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

    it('should turn the state into a validator when eth2 is chosen, keeping none of the address account data', async () => {
      wrapper = createWrapper(createNewBlockchainAccount());

      await choose(Blockchain.ETH2);

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

    it('should carry the addresses already typed across a chain change, since only the chain was answered', async () => {
      const started = createNewBlockchainAccount();
      started.data = [{ address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null }];
      wrapper = createWrapper(started);

      await choose(Blockchain.BTC);

      expect(lastModel().data).toStrictEqual(started.data);
    });

    it('should leave an account being edited on its own chain, which is not up for choosing', async () => {
      wrapper = createWrapper(xpubAccount());

      await choose(Blockchain.ETH2);

      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });

    it('should never leave the chain and the account type disagreeing, in any emitted state', async () => {
      wrapper = createWrapper(createNewBlockchainAccount());

      await choose(Blockchain.ETH2);

      const states = wrapper.emitted<[AccountManageState]>('update:modelValue') ?? [];
      expect(states.length).toBeGreaterThan(0);
      for (const [state] of states)
        expect(state.type === 'validator').toBe(state.chain === Blockchain.ETH2);
    });

    it('should not report an edit on mount, since opening on a chain is not choosing one', () => {
      wrapper = createWrapper(createNewBlockchainAccount());

      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });
  });
});
