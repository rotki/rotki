import type { Ref } from 'vue';
import type { Eth2Validator } from '@/types/balances';
import type {
  AccountPayload,
  BlockchainAccountBalance,
  XpubAccountPayload,
} from '@/types/blockchain/accounts';
import type { Module } from '@/types/modules';
import { assert, bigNumberify, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useBlockchains } from '@/composables/blockchain';
import { useBlockchainAccounts } from '@/composables/blockchain/accounts';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useMessageStore } from '@/store/message';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { isBtcChain } from '@/types/blockchain/chains';
import { getAccountAddress, getChain } from '@/utils/blockchain/accounts/utils';
import { logger } from '@/utils/logging';
import { getKeyType, guessPrefix } from '@/utils/xpub';

interface AccountManageMode {
  readonly mode: 'edit' | 'add';
}

export interface XpubManage extends AccountManageMode {
  chain: Blockchain.BTC | Blockchain.BCH;
  type: 'xpub';
  data: XpubAccountPayload;
}

export interface StakingValidatorManage extends AccountManageMode {
  chain: Blockchain.ETH2;
  type: 'validator';
  data: Eth2Validator;
}

export interface AccountManageAdd extends AccountManageMode {
  readonly mode: 'add';
  chain: string;
  type: 'account';
  data: AccountPayload[];
  /**
   * Adds from all evm addresses if enabled.
   */
  modules?: Module[];
}

export interface AccountManageEdit extends AccountManageMode {
  readonly mode: 'edit';
  chain: string;
  type: 'account';
  data: AccountPayload;
}

export interface AccountAgnosticManage extends AccountManageMode {
  readonly mode: 'edit';
  category: string;
  type: 'group';
  chain: undefined;
  data: AccountPayload;
}

export type AccountManage = AccountManageAdd | AccountManageEdit;

export type AccountManageState = AccountManage | StakingValidatorManage | XpubManage | AccountAgnosticManage;

export function createNewBlockchainAccount(): AccountManageAdd {
  return {
    chain: 'all',
    data: [
      {
        address: '',
        tags: null,
      },
    ],
    mode: 'add',
    type: 'account',
  };
}

export function editBlockchainAccount(account: BlockchainAccountBalance): AccountManageState {
  if ('publicKey' in account.data) {
    const { index, ownershipPercentage = '100', publicKey } = account.data;
    return {
      chain: Blockchain.ETH2,
      data: {
        ownershipPercentage: ownershipPercentage || '100',
        publicKey,
        validatorIndex: index.toString(),
      },
      mode: 'edit',
      type: 'validator',
    } satisfies StakingValidatorManage;
  }
  else if ('xpub' in account.data) {
    const chain = getChain(account);
    assert(chain && isBtcChain(chain));
    const prefix = guessPrefix(account.data.xpub);
    return {
      chain,
      data: {
        label: account.label,
        tags: account.tags ?? null,
        xpub: {
          derivationPath: account.data.derivationPath ?? '',
          xpub: account.data.xpub,
          xpubType: getKeyType(prefix),
        },
      },
      mode: 'edit',
      type: 'xpub',
    } satisfies XpubManage;
  }
  else if (account.type === 'group' && account.chains.length > 1) {
    assert(account.category);
    const address = getAccountAddress(account);
    return {
      category: account.category,
      chain: undefined,
      data: {
        address,
        label: account.label === address ? undefined : account.label,
        tags: account.tags ?? null,
      },
      mode: 'edit',
      type: 'group',
    } satisfies AccountAgnosticManage;
  }
  else {
    const chain = getChain(account);
    assert(chain);
    const address = getAccountAddress(account);
    return {
      chain,
      data: {
        address,
        label: account.label === address ? undefined : account.label,
        tags: account.tags ?? null,
      },
      mode: 'edit',
      type: 'account',
    } satisfies AccountManageEdit;
  }
}

interface UseAccountManageReturn {
  pending: Ref<boolean>;
  errorMessages: Ref<ValidationErrors>;
  save: (state: AccountManageState) => Promise<boolean>;
}

export function useAccountManage(): UseAccountManageReturn {
  const pending = ref(false);
  const errorMessages = ref<ValidationErrors>({});

  const { t } = useI18n({ useScope: 'global' });

  const { updateAccountData, updateAccounts } = useBlockchainAccountsStore();
  const { addAccounts, addEvmAccounts, fetchAccounts, refreshAccounts } = useBlockchains();
  const { addEth2Validator, editEth2Validator, updateEthStakingOwnership } = useEthStaking();
  const { editAccount, editAgnosticAccount } = useBlockchainAccounts();
  const { setMessage } = useMessageStore();

  function handleErrors(error: any, props: Record<string, any> = {}): void {
    logger.error(error);
    let errors = error.message;

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(props);

    if (typeof errors === 'string') {
      setMessage({
        description: t('account_form.error.description', { error: errors }),
        success: false,
        title: t('account_form.error.title'),
      });
    }
    else {
      set(errorMessages, errors);
    }
  }

  async function saveAccount(state: AccountManage): Promise<boolean> {
    const edit = state.mode === 'edit';
    const isEth = state.chain === Blockchain.ETH;

    try {
      set(pending, true);
      if (edit) {
        updateAccounts(state.chain, await editAccount(state.data, state.chain));
      }
      else {
        if (state.chain === 'all') {
          await addEvmAccounts({
            modules: state.modules,
            payload: state.data,
          });
        }
        else {
          await addAccounts(state.chain, {
            modules: isEth ? state.modules : undefined,
            payload: state.data,
          });
        }
      }
    }
    catch (error: any) {
      handleErrors(error);
      return false;
    }
    finally {
      set(pending, false);
    }
    return true;
  }

  async function saveAgnosticAccount(state: AccountAgnosticManage): Promise<boolean> {
    try {
      set(pending, true);
      await editAgnosticAccount(state.category, state.data);
      updateAccountData(state.data);
    }
    catch (error: any) {
      handleErrors(error);
      return false;
    }
    finally {
      set(pending, false);
    }
    return true;
  }

  async function saveXpub(state: XpubManage): Promise<boolean> {
    const edit = state.mode === 'edit';

    const chain = state.chain;
    try {
      set(pending, true);
      if (edit) {
        await editAccount(state.data, chain);
        startPromise(fetchAccounts(chain));
      }
      else {
        await addAccounts(chain, state.data);
      }
    }
    catch (error: any) {
      handleErrors(error, {
        derivationPath: '',
        xpub: '',
      });
      return false;
    }
    finally {
      set(pending, false);
    }
    return true;
  }

  async function saveValidator(state: StakingValidatorManage): Promise<boolean> {
    set(pending, true);

    const payload = state.data;
    const isEdit = state.mode === 'edit';
    const result = isEdit ? await editEth2Validator(payload) : await addEth2Validator(payload);

    if (result.success) {
      if (isEdit) {
        assert(payload.publicKey);
        assert(payload.ownershipPercentage);
        updateEthStakingOwnership(payload.publicKey, bigNumberify(payload.ownershipPercentage));
        startPromise(fetchAccounts(Blockchain.ETH2));
      }
      else {
        startPromise(refreshAccounts(Blockchain.ETH2));
      }
    }
    else if (typeof result.message === 'string') {
      let description: string;
      let title: string;

      if (isEdit) {
        title = t('actions.edit_eth2_validator.error.title');
        description = t('actions.edit_eth2_validator.error.description', {
          id: payload.publicKey || payload.validatorIndex || '',
          message: result.message,
        });
      }
      else {
        title = t('actions.add_eth2_validator.error.title');
        description = t('actions.add_eth2_validator.error.description', {
          id: payload.publicKey || payload.validatorIndex || '',
          message: result.message,
        });
      }

      setMessage({
        description,
        success: false,
        title,
      });
    }
    else {
      set(errorMessages, result.message);
    }

    set(pending, false);
    return result.success;
  }

  const save = async (state: AccountManageState): Promise<boolean> => {
    switch (state.type) {
      case 'account':
        return saveAccount(state);
      case 'validator':
        return saveValidator(state);
      case 'xpub':
        return saveXpub(state);
      case 'group':
        return saveAgnosticAccount(state);
    }
  };

  return {
    errorMessages,
    pending,
    save,
  };
}
