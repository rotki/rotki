import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
        AccountSelector: true,
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
});
