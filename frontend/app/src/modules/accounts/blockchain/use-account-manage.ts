import type { Ref } from 'vue';
import type {
  AccountPayload,
  BlockchainAccountBalance,
  ValidatorData,
  XpubAccountPayload,
  XpubData,
} from '@/modules/accounts/blockchain-accounts';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { Module } from '@/modules/core/common/modules';
import { assert, bigNumberify, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getAccountAddress, getChain } from '@/modules/accounts/account-utils';
import { EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { additionError, isNothingButCancelled } from '@/modules/accounts/blockchain/addition-outcome';
import { useAccountEdits } from '@/modules/accounts/use-account-edits';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
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

function buildValidatorManage(data: ValidatorData): StakingValidatorManage {
  const { index, ownershipPercentage = '100', publicKey } = data;
  return {
    chain: Blockchain.ETH2,
    data: {
      ownershipPercentage: ownershipPercentage || '100',
      publicKey,
      validatorIndex: index.toString(),
    },
    mode: 'edit',
    type: 'validator',
  };
}

function buildXpubManage(account: BlockchainAccountBalance, data: XpubData): XpubManage {
  const chain = getChain(account);
  assert(chain && isBtcChain(chain));
  const prefix = guessPrefix(data.xpub);
  return {
    chain,
    data: {
      label: account.label,
      tags: account.tags ?? null,
      xpub: {
        derivationPath: data.derivationPath ?? '',
        xpub: data.xpub,
        xpubType: getKeyType(prefix),
      },
    },
    mode: 'edit',
    type: 'xpub',
  };
}

function buildGroupManage(account: BlockchainAccountBalance): AccountAgnosticManage {
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
  };
}

function buildAddressManage(account: BlockchainAccountBalance): AccountManageEdit {
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
  };
}

export function editBlockchainAccount(account: BlockchainAccountBalance): AccountManageState {
  if ('publicKey' in account.data)
    return buildValidatorManage(account.data);

  if ('xpub' in account.data)
    return buildXpubManage(account, account.data);

  if (account.type === 'group' && account.chains.length > 1)
    return buildGroupManage(account);

  return buildAddressManage(account);
}

interface UseAccountManageReturn {
  pending: Readonly<Ref<boolean>>;
  modelErrorMessages: Ref<ValidationErrors>;
  saveError: Readonly<Ref<string>>;
  saveErrorIsPremium: Readonly<Ref<boolean>>;
  save: (state: AccountManageState) => Promise<boolean>;
  resetSaveError: () => void;
}

export function useAccountManage(): UseAccountManageReturn {
  const pending = shallowRef<boolean>(false);
  const modelErrorMessages = ref<ValidationErrors>({});
  const saveError = shallowRef<string>('');
  const saveErrorIsPremium = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });

  const { updateAccountData, updateAccounts } = useBlockchainAccountsStore();
  const { addAccounts, fetchAccounts, refreshAccounts } = useBlockchainAccountManagement();
  const { addEth2Validator, editEth2Validator, updateEthStakingOwnership } = useEthStaking();
  const { editAccount, editAgnosticAccount } = useAccountEdits();
  const { showErrorMessage } = useNotifications();

  function handleErrors(error: unknown, props: Record<string, any> = {}): void {
    logger.error(error);
    let errors: ValidationErrors | string = getErrorMessage(error);

    if (!(error instanceof ApiValidationError)) {
      const parsed = new ApiValidationError(errors);
      if (Object.keys(parsed.errors).length > 0)
        error = parsed;
    }

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(props);

    if (typeof errors === 'string') {
      showErrorMessage(t('account_form.error.title'), t('account_form.error.description', { error: errors }));
    }
    else {
      set(modelErrorMessages, errors);
    }
  }

  const additionFallback = (count: number): string =>
    t('account_form.error.addition_failed', { count }, count);

  /**
   * Adds or edits an account.
   *
   * @returns whether the dialog should close. Nothing added with something failed keeps it open so
   * the user can correct the input; a partial success closes it, because the failures have already
   * been reported by the mechanism and the accounts that did land are real.
   */
  async function saveAccount(state: AccountManage): Promise<boolean> {
    const edit = state.mode === 'edit';
    const isEth = state.chain === Blockchain.ETH;

    try {
      set(pending, true);
      if (edit) {
        updateAccounts(state.chain, await editAccount(state.data, state.chain));
        return true;
      }

      // `'all'` is the form's word for every EVM chain; the mechanism's is the pseudo-chain.
      const chain = state.chain === 'all' ? EVM_PSEUDO_CHAIN : state.chain;
      const summary = await addAccounts(chain, {
        modules: isEth || state.chain === 'all' ? state.modules : undefined,
        payload: state.data,
      }, { wait: true });

      if (summary.added.length === 0 && summary.failed.length > 0) {
        handleErrors(additionError(summary.failed, additionFallback(summary.failed.length)));
        return false;
      }

      if (isNothingButCancelled(summary))
        return false;
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
        startPromise(fetchAccounts({ blockchain: chain }));
      }
      else {
        // Awaited, so an xpub that fails to add keeps its dialog open rather than closing as if it
        // had worked. `handleErrors` is given the xpub props so `ApiValidationError` can still fill
        // in per-field errors.
        const summary = await addAccounts(chain, state.data, { wait: true });
        if (summary.added.length === 0 && summary.failed.length > 0) {
          handleErrors(additionError(summary.failed, additionFallback(summary.failed.length)), {
            derivationPath: '',
            xpub: '',
          });
          return false;
        }

        if (isNothingButCancelled(summary))
          return false;
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

    try {
      const payload = state.data;
      const isEdit = state.mode === 'edit';
      const result = isEdit ? await editEth2Validator(payload) : await addEth2Validator(payload);

      if (result.success) {
        if (isEdit) {
          assert(payload.publicKey);
          assert(payload.ownershipPercentage);
          updateEthStakingOwnership(payload.publicKey, bigNumberify(payload.ownershipPercentage));
          startPromise(fetchAccounts({ blockchain: Blockchain.ETH2 }));
        }
        else {
          startPromise(refreshAccounts({ blockchain: Blockchain.ETH2 }));
        }
        return true;
      }

      if (typeof result.message === 'string') {
        set(saveErrorIsPremium, result.message.includes('limit exceeded'));
        const friendly = result.message.includes('failed due to missing API key')
          ? t('account_form.error.validator_needs_credentials')
          : result.message;
        set(saveError, friendly);
      }
      else {
        set(modelErrorMessages, result.message);
      }
      return false;
    }
    catch (error: unknown) {
      logger.error(error);
      if (error instanceof ApiValidationError) {
        const validation = error.getValidationErrors({
          ownershipPercentage: '',
          publicKey: '',
          validatorIndex: '',
        });
        if (typeof validation === 'string')
          set(saveError, validation);
        else
          set(modelErrorMessages, validation);
      }
      else {
        set(saveError, getErrorMessage(error));
      }
      return false;
    }
    finally {
      set(pending, false);
    }
  }

  function resetSaveError(): void {
    set(saveError, '');
    set(saveErrorIsPremium, false);
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
    modelErrorMessages,
    pending: readonly(pending),
    resetSaveError,
    save,
    saveError: readonly(saveError),
    saveErrorIsPremium: readonly(saveErrorIsPremium),
  };
}
