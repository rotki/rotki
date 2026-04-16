import type { Ref } from 'vue';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { ActionStatus } from '@/modules/core/common/action';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { type BigNumber, Blockchain, type EthValidatorFilter } from '@rotki/common';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { Section } from '@/modules/core/common/status';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { usePremium } from '@/modules/premium/use-premium';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';
import { useEthValidatorFetching } from '@/modules/staking/eth/use-eth-validator-fetching';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

interface UseEthStakingReturn {
  validatorsLimitInfo: Readonly<Ref<{ showWarning: boolean; limit: number; total: number }>>;
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
  const { isEth2Enabled, updateEthStakingOwnership } = blockchainValidatorsStore;
  const { fetchEthStakingValidators } = useEthValidatorFetching();

  const premium = usePremium();
  const { runTask } = useTaskHandler();
  const { showErrorMessage } = useNotifications();
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
    const outcome = await runTask<boolean, TaskMeta>(
      async () => addEth2ValidatorCaller(payload),
      {
        type: TaskType.ADD_ETH2_VALIDATOR,
        meta: {
          description: t('actions.add_eth2_validator.task.description', { id }),
          title: t('actions.add_eth2_validator.task.title'),
        },
      },
    );

    if (outcome.success) {
      if (outcome.result) {
        resetStatus();
        resetStatus({ section: Section.STAKING_ETH2_DEPOSITS });
        resetStatus({ section: Section.STAKING_ETH2_STATS });
      }

      return {
        message: '',
        success: outcome.result,
      };
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);

      let message: ValidationErrors | string = outcome.message;
      if (outcome.error instanceof ApiValidationError)
        message = outcome.error.getValidationErrors(payload);

      return {
        message,
        success: false,
      };
    }

    return { message: '', success: false };
  };

  const editEth2Validator = async (payload: Eth2Validator): Promise<ActionStatus<ValidationErrors | string>> => {
    if (!isEth2Enabled())
      return { message: '', success: false };

    try {
      const success = await editEth2ValidatorCaller(payload);
      return { message: '', success };
    }
    catch (error: unknown) {
      logger.error(error);
      let message: ValidationErrors | string = getErrorMessage(error);
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
    catch (error: unknown) {
      logger.error(error);
      showErrorMessage(t('actions.delete_eth2_validator.error.title'), t('actions.delete_eth2_validator.error.description', {
        message: getErrorMessage(error),
      }));
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
