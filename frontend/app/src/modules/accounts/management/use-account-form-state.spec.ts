import { Blockchain } from '@rotki/common';
import { assert, beforeEach, describe, expect, it } from 'vitest';
import { type Ref, ref } from 'vue';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import {
  type AccountManageState,
  createNewBlockchainAccount,
  type XpubManage,
} from '@/modules/accounts/blockchain/use-account-manage';
import { useAccountFormState } from '@/modules/accounts/management/use-account-form-state';

function xpub(mode: 'add' | 'edit', chain: Blockchain.BTC | Blockchain.BCH = Blockchain.BTC): XpubManage {
  return {
    chain,
    data: {
      tags: null,
      xpub: { derivationPath: '', xpub: '', xpubType: XpubKeyType.ZPUB },
    },
    mode,
    type: 'xpub',
  };
}

/** An account group has no chain of its own, which is the only state that reaches the no-chain guards. */
function groupAccount(): AccountManageState {
  return {
    category: 'evm',
    chain: undefined,
    data: { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null },
    mode: 'edit',
    type: 'group',
  };
}

function validator(mode: 'add' | 'edit' = 'edit'): AccountManageState {
  return { chain: Blockchain.ETH2, data: {}, mode, type: 'validator' };
}

function accountOn(chain: string): AccountManageState {
  return { ...createNewBlockchainAccount(), chain };
}

describe('useAccountFormState', () => {
  let modelValue: Ref<AccountManageState>;

  beforeEach(() => {
    modelValue = ref<AccountManageState>(createNewBlockchainAccount());
  });

  /**
   * The chain implies the kind of account, so a choice replaces the whole state. Writing the chain
   * alone would leave it paired with the previous kind, which the union does not admit.
   */
  describe('choosing a chain', () => {
    it('should answer eth2 with a validator', () => {
      const { selectChain } = useAccountFormState(modelValue);

      selectChain(Blockchain.ETH2);

      expect(get(modelValue)).toStrictEqual({
        chain: Blockchain.ETH2,
        data: {},
        mode: 'add',
        type: 'validator',
      });
    });

    it('should answer any other chain with an address account', () => {
      set(modelValue, validator('add'));
      const { selectChain } = useAccountFormState(modelValue);

      selectChain(Blockchain.BTC);

      expect(get(modelValue).type).toBe('account');
      expect(get(modelValue).chain).toBe(Blockchain.BTC);
    });

    /** Only the chain was answered, so what the user already typed is not thrown away. */
    it('should carry already typed addresses across the change', () => {
      const typed = [{ address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null }];
      set(modelValue, { ...createNewBlockchainAccount(), data: typed });
      const { selectChain } = useAccountFormState(modelValue);

      selectChain(Blockchain.BTC);

      expect(get(modelValue).data).toStrictEqual(typed);
    });

    /** An xpub's data is not a list of addresses, so there is nothing to carry over. */
    it('should not carry xpub data across the change', () => {
      set(modelValue, xpub('add'));
      const { selectChain } = useAccountFormState(modelValue);

      selectChain(Blockchain.ETH);

      expect(get(modelValue).data).toStrictEqual(createNewBlockchainAccount().data);
    });

    it('should leave an account being edited on its chain', () => {
      set(modelValue, xpub('edit'));
      const before = get(modelValue);
      const { selectChain } = useAccountFormState(modelValue);

      selectChain(Blockchain.ETH2);

      expect(get(modelValue)).toBe(before);
    });

    it('should ignore a cleared chain', () => {
      const before = get(modelValue);
      const { selectChain } = useAccountFormState(modelValue);

      selectChain(undefined);

      expect(get(modelValue)).toBe(before);
    });
  });

  describe('editing a validator', () => {
    it('should keep the rest of the state around the new validator', () => {
      set(modelValue, validator());
      const { setValidator } = useAccountFormState(modelValue);

      setValidator({ publicKey: '0xabc' });

      expect(get(modelValue)).toStrictEqual({
        chain: Blockchain.ETH2,
        data: { publicKey: '0xabc' },
        mode: 'edit',
        type: 'validator',
      });
    });

    /** Writing validator data onto an address account would produce a state nothing expects. */
    it('should refuse to write validator data onto another kind of account', () => {
      const before = get(modelValue);
      const { setValidator } = useAccountFormState(modelValue);

      setValidator({ publicKey: '0xabc' });

      expect(get(modelValue)).toBe(before);
    });
  });

  /** An xpub pasted into the address field is a request to switch the form over to xpub entry. */
  describe('detecting a pasted xpub', () => {
    it('should turn the state into an xpub carrying the key', async () => {
      set(modelValue, accountOn(Blockchain.BTC));
      const { handleDetectedXpub } = useAccountFormState(modelValue);

      await handleDetectedXpub('zpub6r');

      const state = get(modelValue);
      assert(state.type === 'xpub');
      expect(state.data.xpub.xpub).toBe('zpub6r');
      expect(state.chain).toBe(Blockchain.BTC);
    });

    it('should default a bitcoin cash xpub to its own key type', async () => {
      set(modelValue, accountOn(Blockchain.BCH));
      const { handleDetectedXpub } = useAccountFormState(modelValue);

      await handleDetectedXpub('xpub6r');

      const state = get(modelValue);
      assert(state.type === 'xpub');
      expect(state.data.xpub.xpubType).toBe(XpubKeyType.XPUB);
    });

    it('should default a bitcoin xpub to zpub', async () => {
      set(modelValue, accountOn(Blockchain.BTC));
      const { handleDetectedXpub } = useAccountFormState(modelValue);

      await handleDetectedXpub('zpub6r');

      const state = get(modelValue);
      assert(state.type === 'xpub');
      expect(state.data.xpub.xpubType).toBe(XpubKeyType.ZPUB);
    });

    /** Only bitcoin chains have xpubs, so on anything else the paste is not one. */
    it('should ignore it on a chain that has no xpubs', async () => {
      set(modelValue, accountOn(Blockchain.ETH));
      const before = get(modelValue);
      const { handleDetectedXpub } = useAccountFormState(modelValue);

      await handleDetectedXpub('zpub6r');

      expect(get(modelValue)).toBe(before);
    });
  });

  describe('detecting a pasted address', () => {
    it('should put the address into the state', async () => {
      set(modelValue, accountOn(Blockchain.ETH));
      const { handleDetectedAddress } = useAccountFormState(modelValue);

      await handleDetectedAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306');

      expect(get(modelValue)).toStrictEqual({
        chain: Blockchain.ETH,
        data: [{ address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null }],
        mode: 'add',
        type: 'account',
      });
    });

    /** A `bitcoincash:` address names its own chain, so the form follows it off bitcoin. */
    it('should move a bitcoin cash address off bitcoin', async () => {
      set(modelValue, accountOn(Blockchain.BTC));
      const { handleDetectedAddress } = useAccountFormState(modelValue);

      await handleDetectedAddress('bitcoincash:qpm2');

      expect(get(modelValue).chain).toBe(Blockchain.BCH);
    });

    it('should leave a plain address on bitcoin', async () => {
      set(modelValue, accountOn(Blockchain.BTC));
      const { handleDetectedAddress } = useAccountFormState(modelValue);

      await handleDetectedAddress('1A1zP1eP5Q');

      expect(get(modelValue).chain).toBe(Blockchain.BTC);
    });

    it('should ignore it on an account group, which has no chain', async () => {
      set(modelValue, groupAccount());
      const before = get(modelValue);
      const { handleDetectedAddress } = useAccountFormState(modelValue);

      await handleDetectedAddress('0x9531C059098e3d194fF87FebB587aB07B30B1306');

      expect(get(modelValue)).toBe(before);
    });

    /** Coming back from xpub entry has to leave an address account behind, not an empty xpub. */
    it('should turn an xpub state back into an address account', async () => {
      set(modelValue, xpub('add'));
      const { handleDetectedAddress } = useAccountFormState(modelValue);

      await handleDetectedAddress('1A1zP1eP5Q');

      expect(get(modelValue).type).toBe('account');
    });
  });
});
