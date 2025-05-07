import type { ActionStatus } from '@/types/action';
import type { Eth2Validator } from '@/types/balances';
import type { BlockchainAccount, ValidatorData } from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import type { ComputedRef } from 'vue';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useMessageStore } from '@/store/message';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';
import { type BigNumber, bigNumberify, Blockchain } from '@rotki/common';

interface UseEthStakingReturn {
  validatorsLimitInfo: ComputedRef<{ showWarning: boolean; limit: number; total: number }>;
  fetchEthStakingValidators: () => Promise<void>;
  addEth2Validator: (payload: Eth2Validator) => Promise<ActionStatus<ValidationErrors | string>>;
  editEth2Validator: (payload: Eth2Validator) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteEth2Validators: (validators: string[]) => Promise<boolean>;
  updateEthStakingOwnership: (publicKey: string, newOwnershipPercentage: BigNumber) => void;
}

export function useEthStaking(): UseEthStakingReturn {
  const {
    addEth2Validator: addEth2ValidatorCaller,
    deleteEth2Validators: deleteEth2ValidatorsCaller,
    editEth2Validator: editEth2ValidatorCaller,
  } = useBlockchainAccountsApi();
  const { getAccounts, updateAccounts } = useBlockchainAccountsStore();
  const balancesStore = useBalancesStore();
  const { balances } = storeToRefs(balancesStore);
  const { updateBalances } = balancesStore;

  const blockchainValidatorsStore = useBlockchainValidatorsStore();
  const { ethStakingValidators, stakingValidatorsLimits } = storeToRefs(blockchainValidatorsStore);
  const { fetchEthStakingValidators } = blockchainValidatorsStore;
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const premium = usePremium();
  const { awaitTask } = useTaskStore();
  const { setMessage } = useMessageStore();
  const { t } = useI18n({ useScope: 'global' });
  const { resetStatus } = useStatusUpdater(Section.STAKING_ETH2);

  const isEth2Enabled = (): boolean => get(activeModules).includes(Module.ETH2);

  const addEth2Validator = async (payload: Eth2Validator): Promise<ActionStatus<ValidationErrors | string>> => {
    if (!isEth2Enabled()) {
      return {
        message: '',
        success: false,
      };
    }
    const id = payload.publicKey || payload.validatorIndex;
    try {
      const taskType = TaskType.ADD_ETH2_VALIDATOR;
      const { taskId } = await addEth2ValidatorCaller(payload);
      const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        description: t('actions.add_eth2_validator.task.description', {
          id,
        }),
        title: t('actions.add_eth2_validator.task.title'),
      });
      if (result) {
        resetStatus();
        resetStatus({ section: Section.STAKING_ETH2_DEPOSITS });
        resetStatus({ section: Section.STAKING_ETH2_STATS });
      }

      return {
        message: '',
        success: result,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      let message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(payload);

      return {
        message,
        success: false,
      };
    }
  };

  const editEth2Validator = async (payload: Eth2Validator): Promise<ActionStatus<ValidationErrors | string>> => {
    if (!isEth2Enabled())
      return { message: '', success: false };

    try {
      const success = await editEth2ValidatorCaller(payload);
      return { message: '', success };
    }
    catch (error: any) {
      logger.error(error);
      let message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(payload);

      return {
        message,
        success: false,
      };
    }
  };

  const deleteEth2Validators = async (validators: string[]): Promise<boolean> => {
    try {
      const pendingRemoval = get(ethStakingValidators).filter(account => validators.includes(account.publicKey));
      const success = await deleteEth2ValidatorsCaller(pendingRemoval);
      if (success) {
        if (get(premium)) {
          const remainingValidators = getAccounts(Blockchain.ETH2).filter(
            ({ data }) => 'publicKey' in data && !validators.includes(data.publicKey),
          );
          updateAccounts(Blockchain.ETH2, remainingValidators);
        }
        else {
          await fetchEthStakingValidators();
        }
      }
      return success;
    }
    catch (error: any) {
      logger.error(error);
      setMessage({
        description: t('actions.delete_eth2_validator.error.description', {
          message: error.message,
        }),
        success: false,
        title: t('actions.delete_eth2_validator.error.title'),
      });
      return false;
    }
  };

  /**
   * Adjusts the balances for an ethereum staking validator based on the percentage of ownership.
   *
   * @param publicKey the validator's public key is used to identify the balance
   * @param newOwnershipPercentage the ownership percentage of the validator after the edit
   */
  const updateEthStakingOwnership = (publicKey: string, newOwnershipPercentage: BigNumber): void => {
    const isValidator = (x: BlockchainAccount): x is BlockchainAccount<ValidatorData> => x.data.type === 'validator';
    const validators = [...getAccounts(Blockchain.ETH2).filter(isValidator)];
    const validatorIndex = validators.findIndex(validator => validator.data.publicKey === publicKey);
    const [validator] = validators.splice(validatorIndex, 1);
    const oldOwnershipPercentage = bigNumberify(validator.data.ownershipPercentage || 100);
    validators.push({
      ...validator,
      data: {
        ...validator.data,
        ownershipPercentage: newOwnershipPercentage.isEqualTo(100) ? undefined : newOwnershipPercentage.toString(),
      },
    });

    updateAccounts(Blockchain.ETH2, validators);

    const eth2 = get(balances)[Blockchain.ETH2];
    if (!eth2[publicKey])
      return;

    const ETH2_ASSET = Blockchain.ETH2.toUpperCase();

    const { amount, usdValue } = eth2[publicKey].assets[ETH2_ASSET];

    // we should not need to update anything if amount and value are zero
    if (amount.isZero() && usdValue.isZero())
      return;

    const calc = (value: BigNumber, oldPercentage: BigNumber, newPercentage: BigNumber): BigNumber =>
      value.dividedBy(oldPercentage).multipliedBy(newPercentage);

    const newAmount = calc(amount, oldOwnershipPercentage, newOwnershipPercentage);

    const newValue = calc(usdValue, oldOwnershipPercentage, newOwnershipPercentage);

    const updatedBalance = {
      [publicKey]: {
        assets: {
          [ETH2_ASSET]: {
            amount: newAmount,
            usdValue: newValue,
          },
        },
        liabilities: {},
      },
    };

    updateBalances(Blockchain.ETH2, {
      perAccount: {
        [Blockchain.ETH2]: {
          ...eth2,
          ...updatedBalance,
        },
      },
      totals: {
        assets: {},
        liabilities: {},
      },
    });
  };

  const validatorsLimitInfo = computed(() => {
    const limits = get(stakingValidatorsLimits);
    if (!limits) {
      return {
        limit: 0,
        showWarning: false,
        total: 0,
      };
    }

    const { limit, total } = limits;
    return {
      limit,
      showWarning: limit > 0 && limit <= total,
      total,
    };
  });

  return {
    addEth2Validator,
    deleteEth2Validators,
    editEth2Validator,
    fetchEthStakingValidators,
    updateEthStakingOwnership,
    validatorsLimitInfo,
  };
}
