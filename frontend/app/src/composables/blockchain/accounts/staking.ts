import type { ComputedRef } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { Eth2Validator } from '@/types/balances';
import type { TaskMeta } from '@/types/task';
import { type BigNumber, Blockchain, type EthValidatorFilter } from '@rotki/common';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';

interface UseEthStakingReturn {
  validatorsLimitInfo: ComputedRef<{ showWarning: boolean; limit: number; total: number }>;
  fetchEthStakingValidators: (payload?: EthValidatorFilter) => Promise<void>;
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

  const blockchainValidatorsStore = useBlockchainValidatorsStore();
  const { ethStakingValidators, stakingValidatorsLimits } = storeToRefs(blockchainValidatorsStore);
  const { fetchEthStakingValidators, isEth2Enabled, updateEthStakingOwnership } = blockchainValidatorsStore;

  const premium = usePremium();
  const { awaitTask } = useTaskStore();
  const { setMessage } = useMessageStore();
  const { t } = useI18n({ useScope: 'global' });
  const { resetStatus } = useStatusUpdater(Section.STAKING_ETH2);

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
