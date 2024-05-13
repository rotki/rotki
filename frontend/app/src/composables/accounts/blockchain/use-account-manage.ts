import { Blockchain } from '@rotki/common/lib/blockchain';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { isBtcChain } from '@/types/blockchain/chains';
import { XpubPrefix } from '@/utils/xpub';
import type { Module } from '@/types/modules';
import type { AccountPayload, BlockchainAccountWithBalance, XpubAccountPayload } from '@/types/blockchain/accounts';
import type { Eth2Validator } from '@/types/balances';

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
  /**
   * The original account ownership percentage, needed when editing the account.
   */
  ownershipPercentage?: number;
}

export interface AccountManageAdd extends AccountManageMode {
  readonly mode: 'add';
  chain: string;
  type: 'account';
  data: AccountPayload[];
  /**
   * Adds from all evm addresses if enabled.
   */
  evm?: boolean;
  /**
   * The specified modules will be enabled for the account.
   */
  modules?: Module[];
}

export interface AccountManageEdit extends AccountManageMode {
  readonly mode: 'edit';
  chain: string;
  type: 'account';
  data: AccountPayload;
}

export type AccountManage = AccountManageAdd | AccountManageEdit;

export type AccountManageState = AccountManage | StakingValidatorManage | XpubManage;

export function createNewBlockchainAccount(): AccountManageAdd {
  return {
    mode: 'add',
    type: 'account',
    chain: Blockchain.ETH,
    data: [
      {
        address: '',
        tags: null,
      },
    ],
  };
}

export function editBlockchainAccount(account: BlockchainAccountWithBalance): AccountManageState {
  if ('publicKey' in account.data) {
    const { ownershipPercentage, publicKey, index } = account.data;
    return {
      mode: 'edit',
      type: 'validator',
      chain: Blockchain.ETH2,
      data: {
        ownershipPercentage,
        publicKey,
        validatorIndex: index.toString(),
      },
    } satisfies StakingValidatorManage;
  }
  else if ('xpub' in account.data) {
    const chain = account.chain;
    assert(isBtcChain(chain));
    const match = isPrefixed(account.data.xpub);
    const prefix = match?.[1] ?? XpubPrefix.XPUB;
    return {
      mode: 'edit',
      type: 'xpub',
      chain,
      data: {
        tags: account.tags ?? null,
        label: account.label,
        xpub: {
          xpub: account.data.xpub,
          derivationPath: account.data.derivationPath ?? '',
          xpubType: getKeyType(prefix as XpubPrefix),
        },
      },
    } satisfies XpubManage;
  }
  else {
    return {
      mode: 'edit',
      type: 'account',
      chain: account.chain,
      data: {
        tags: account.tags ?? null,
        label: account.label,
        address: account.data.address,
      },

    } satisfies AccountManageEdit;
  }
}

export function useAccountManage() {
  const pending = ref(false);
  const errorMessages = ref<ValidationErrors>({});

  const { t } = useI18n();

  const { addAccounts, addEvmAccounts, fetchAccounts, refreshAccounts } = useBlockchains();
  const { addEth2Validator, editEth2Validator, updateEthStakingOwnership } = useEthStaking();
  const { editAccount } = useBlockchainAccounts();
  const { setMessage } = useMessageStore();

  function handleErrors(error: any, props: Record<string, any> = {}) {
    logger.error(error);
    let errors = error.message;

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors(props);

    if (typeof errors === 'string') {
      setMessage({
        description: t('account_form.error.description', { error: errors }),
        title: t('account_form.error.title'),
        success: false,
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
        await editAccount(state.data, state.chain);
        startPromise(fetchAccounts(state.chain));
      }
      else {
        if (state.evm) {
          await addEvmAccounts({
            payload: state.data,
            modules: state.modules,
          });
        }
        else {
          await addAccounts(state.chain, {
            payload: state.data,
            modules: isEth ? state.modules : undefined,
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
        xpub: '',
        derivationPath: '',
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
        updateEthStakingOwnership(
          payload.publicKey,
          bigNumberify(state?.ownershipPercentage ?? 100),
          bigNumberify(payload.ownershipPercentage),
        );
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
        title,
        success: false,
      });
    }
    else {
      set(errorMessages, result.message);
    }

    set(pending, false);
    return result.success;
  }

  const save = (state: AccountManageState): Promise<boolean> => {
    switch (state.type) {
      case 'account':
        return saveAccount(state);
      case 'validator':
        return saveValidator(state);
      case 'xpub':
        return saveXpub(state);
    }
  };

  return {
    pending,
    errorMessages,
    save,
  };
}
