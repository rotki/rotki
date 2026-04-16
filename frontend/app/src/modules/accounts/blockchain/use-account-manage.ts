import type { Ref } from 'vue';
import type {
  AccountPayload,
  BlockchainAccountBalance,
  XpubAccountPayload,
} from '@/modules/accounts/blockchain-accounts';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { Module } from '@/modules/core/common/modules';
import { assert, bigNumberify, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getAccountAddress, getChain } from '@/modules/accounts/account-utils';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { useBlockchainAccounts } from '@/modules/accounts/use-blockchain-accounts';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { getKeyType, guessPrefix } from '@/modules/accounts/xpub';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { isBtcChain } from '@/modules/core/common/chains';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';

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

interface AccountManageAdd extends AccountManageMode {
  readonly mode: 'add';
  chain: string;
  type: 'account';
  data: AccountPayload[];
  /**
   * Adds from all evm addresses if enabled.
   */
  modules?: Module[];
}

interface AccountManageEdit extends AccountManageMode {
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
  pending: Readonly<Ref<boolean>>;
  errorMessages: Ref<ValidationErrors>;
  saveError: Readonly<Ref<string>>;
  saveErrorIsPremium: Readonly<Ref<boolean>>;
  save: (state: AccountManageState) => Promise<boolean>;
}

export function useAccountManage(): UseAccountManageReturn {
  const pending = shallowRef<boolean>(false);
  const errorMessages = ref<ValidationErrors>({});
  const saveError = shallowRef<string>('');
  const saveErrorIsPremium = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });

  const { updateAccountData, updateAccounts } = useBlockchainAccountsStore();
  const { addAccounts, addEvmAccounts, fetchAccounts, refreshAccounts } = useBlockchainAccountManagement();
  const { addEth2Validator, editEth2Validator, updateEthStakingOwnership } = useEthStaking();
  const { editAccount, editAgnosticAccount } = useBlockchainAccounts();
  const { showErrorMessage } = useNotifications();

  function handleErrors(error: unknown, props: Record<string, any> = {}): void {
    logger.error(error);
    let errors: ValidationErrors | string = getErrorMessage(error);

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(props);

    if (typeof errors === 'string') {
      showErrorMessage(t('account_form.error.title'), t('account_form.error.description', { error: errors }));
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
    catch (error: unknown) {
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
    catch (error: unknown) {
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
    catch (error: unknown) {
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
    set(saveError, '');
    set(saveErrorIsPremium, false);

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
        startPromise(refreshAccounts({ blockchain: Blockchain.ETH2 }));
      }
    }
    else if (typeof result.message === 'string') {
      set(saveError, result.message);
      set(saveErrorIsPremium, result.message.includes('limit exceeded'));
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
    // eslint-disable-next-line @rotki/composable-return-readonly
    errorMessages,
    pending: readonly(pending),
    save,
    saveError: readonly(saveError),
    saveErrorIsPremium: readonly(saveErrorIsPremium),
  };
}
