import { type BigNumber, Blockchain } from '@rotki/common';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import { Module } from '@/types/modules';
import type { BlockchainAccount, ValidatorData } from '@/types/blockchain/accounts';
import type { Eth2Validator } from '@/types/balances';
import type { ActionStatus } from '@/types/action';
import type { TaskMeta } from '@/types/task';
import type { ComputedRef } from 'vue';

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
    editEth2Validator: editEth2ValidatorCaller,
    deleteEth2Validators: deleteEth2ValidatorsCaller,
  } = useBlockchainAccountsApi();
  const blockchainStore = useBlockchainStore();
  const { updateAccounts, getAccounts, updateBalances } = blockchainStore;
  const { balances } = storeToRefs(blockchainStore);

  const blockchainValidatorsStore = useBlockchainValidatorsStore();
  const { stakingValidatorsLimits, ethStakingValidators } = storeToRefs(blockchainValidatorsStore);
  const { fetchEthStakingValidators } = blockchainValidatorsStore;
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const premium = usePremium();
  const { awaitTask } = useTaskStore();
  const { setMessage } = useMessageStore();
  const { t } = useI18n();
  const { resetStatus } = useStatusUpdater(Section.STAKING_ETH2);

  const isEth2Enabled = (): boolean => get(activeModules).includes(Module.ETH2);

  const addEth2Validator = async (payload: Eth2Validator): Promise<ActionStatus<ValidationErrors | string>> => {
    if (!isEth2Enabled()) {
      return {
        success: false,
        message: '',
      };
    }
    const id = payload.publicKey || payload.validatorIndex;
    try {
      const taskType = TaskType.ADD_ETH2_VALIDATOR;
      const { taskId } = await addEth2ValidatorCaller(payload);
      const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: t('actions.add_eth2_validator.task.title'),
        description: t('actions.add_eth2_validator.task.description', {
          id,
        }),
      });
      if (result) {
        resetStatus();
        resetStatus({ section: Section.STAKING_ETH2_DEPOSITS });
        resetStatus({ section: Section.STAKING_ETH2_STATS });
      }

      return {
        success: result,
        message: '',
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      let message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(payload);

      return {
        success: false,
        message,
      };
    }
  };

  const editEth2Validator = async (payload: Eth2Validator): Promise<ActionStatus<ValidationErrors | string>> => {
    if (!isEth2Enabled())
      return { success: false, message: '' };

    try {
      const success = await editEth2ValidatorCaller(payload);
      return { success, message: '' };
    }
    catch (error: any) {
      logger.error(error);
      let message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(payload);

      return {
        success: false,
        message,
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
        title: t('actions.delete_eth2_validator.error.title'),
        success: false,
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

    const { amount, value } = eth2[publicKey].assets[ETH2_ASSET];

    // we should not need to update anything if amount and value are zero
    if (amount.isZero() && value.isZero())
      return;

    const calc = (value: BigNumber, oldPercentage: BigNumber, newPercentage: BigNumber): BigNumber =>
      value.dividedBy(oldPercentage).multipliedBy(newPercentage);

    const newAmount = calc(amount, oldOwnershipPercentage, newOwnershipPercentage);

    const newValue = calc(value, oldOwnershipPercentage, newOwnershipPercentage);

    const updatedBalance = {
      [publicKey]: {
        assets: {
          [ETH2_ASSET]: {
            amount: newAmount,
            value: newValue,
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
        showWarning: false,
        total: 0,
        limit: 0,
      };
    }

    const { limit, total } = limits;
    return {
      showWarning: limit > 0 && limit <= total,
      total,
      limit,
    };
  });

  return {
    validatorsLimitInfo,
    fetchEthStakingValidators,
    addEth2Validator,
    editEth2Validator,
    deleteEth2Validators,
    updateEthStakingOwnership,
  };
}
