import type { Ref } from 'vue';
import { assert, Blockchain } from '@rotki/common';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import {
  type AccountManageState,
  createNewBlockchainAccount,
  type StakingValidatorManage,
  type XpubManage,
} from '@/modules/accounts/blockchain/use-account-manage';
import { isBtcChain } from '@/modules/core/common/chains';
import { InputMode } from '@/modules/core/common/input-mode';

export interface UseAccountFormStateReturn {
  setValidator: (data: StakingValidatorManage['data']) => void;
  selectChain: (next: string | undefined) => void;
  handleDetectedXpub: (key: string) => Promise<void>;
  handleDetectedAddress: (address: string) => Promise<void>;
}

/**
 * Owns the account form's state transitions, each of which replaces the whole state rather than
 * writing a field into it.
 *
 * @remarks
 * `AccountManageState` is a discriminated union in which the chain implies the kind of account and
 * so the shape of `data`. Writing one field therefore type-checks while producing a state the union
 * does not admit, which is why every transition here builds a complete state.
 */
export function useAccountFormState(modelValue: Ref<AccountManageState>): UseAccountFormStateReturn {
  const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

  const chain = computed<string | undefined>(() => get(modelValue).chain);

  /**
   * A validator edit only ever reaches a state that holds a validator, which is what the guard says.
   * Narrowing first is what lets the rest of the state be carried over as itself, rather than a
   * field being written onto whichever variant happens to be there.
   */
  function setValidator(data: StakingValidatorManage['data']): void {
    const state = get(modelValue);
    if (state.type !== 'validator')
      return;

    set(modelValue, { ...state, data });
  }

  /**
   * Answers a chosen chain with a whole state.
   *
   * @remarks
   * An account being edited already exists on its chain, so there is nothing to choose. Addresses
   * already typed survive the change, since only the chain was answered.
   */
  function selectChain(next: string | undefined): void {
    if (!next || get(modelValue).mode === 'edit')
      return;

    if (get(inputMode) === InputMode.XPUB_ADD)
      set(inputMode, InputMode.MANUAL_ADD);

    if (next === Blockchain.ETH2) {
      set(modelValue, {
        chain: Blockchain.ETH2,
        data: {},
        mode: 'add',
        type: 'validator',
      } satisfies StakingValidatorManage);
      return;
    }

    const addressesTypedForTheOldChain = get(modelValue).data;
    set(modelValue, {
      ...createNewBlockchainAccount(),
      chain: next,
      ...(Array.isArray(addressesTypedForTheOldChain) ? { data: addressesTypedForTheOldChain } : {}),
    });
  }

  /** An xpub pasted into the address field is a request to switch the form over to xpub entry. */
  async function handleDetectedXpub(key: string): Promise<void> {
    const selectedChain = get(chain);
    if (!selectedChain || !isBtcChain(selectedChain))
      return;

    set(inputMode, InputMode.XPUB_ADD);
    await nextTick();

    const current = get(modelValue);
    if (current.type !== 'xpub')
      return;

    set(modelValue, {
      ...current,
      data: {
        ...current.data,
        xpub: {
          ...current.data.xpub,
          xpub: key,
        },
      },
    });
  }

  /** A `bitcoincash:` address pasted while on BTC names its own chain, so the form follows it. */
  async function handleDetectedAddress(address: string): Promise<void> {
    let targetChain = get(chain);
    if (!targetChain)
      return;

    if (targetChain === Blockchain.BTC && address.startsWith('bitcoincash:'))
      targetChain = Blockchain.BCH;

    set(inputMode, InputMode.MANUAL_ADD);
    await nextTick();
    set(modelValue, {
      chain: targetChain,
      data: [{ address, tags: null }],
      mode: 'add',
      type: 'account',
    });
  }

  /** An xpub being edited opens in xpub entry, since that is the account it is. */
  watch(modelValue, (state) => {
    if ('xpub' in state.data && state.mode === 'edit')
      set(inputMode, InputMode.XPUB_ADD);
  }, {
    immediate: true,
  });

  /** Switching entry mode re-shapes the account, since the two modes hold different data. */
  watch(inputMode, (mode) => {
    const selectedChain = get(chain);
    if (get(modelValue).mode === 'edit' || !selectedChain)
      return;

    if (mode === InputMode.XPUB_ADD) {
      assert(isBtcChain(selectedChain));
      set(modelValue, {
        chain: selectedChain,
        data: {
          tags: null,
          xpub: {
            derivationPath: '',
            xpub: '',
            xpubType: selectedChain === Blockchain.BCH ? XpubKeyType.XPUB : XpubKeyType.ZPUB,
          },
        },
        mode: 'add',
        type: 'xpub',
      } satisfies XpubManage);
    }
    else {
      set(modelValue, {
        ...createNewBlockchainAccount(),
        chain: selectedChain,
      });
    }
  });

  return {
    handleDetectedAddress,
    handleDetectedXpub,
    selectChain,
    setValidator,
  };
}
