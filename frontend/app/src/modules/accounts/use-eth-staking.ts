import type { Ref } from 'vue';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { ActionStatus } from '@/modules/core/common/action';
import { type BigNumber, Blockchain, type EthValidatorFilter } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { usePremium } from '@/modules/premium/use-premium';
import { useEthValidatorFetching } from '@/modules/staking/eth/use-eth-validator-fetching';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

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
  const { submitTask } = useNativeTask();
  const { showErrorMessage } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  const addEth2Validator = async (payload: Eth2Validator): Promise<ActionStatus<ValidationErrors | string>> => {
    if (!isEth2Enabled()) {
      return {
        message: '',
        success: false,
      };
    }
    const id = payload.publicKey ?? payload.validatorIndex;
    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.STAKING, ActivityPart.ADD, id ?? ''),
      kind: ActivityKind.STAKING,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => addEth2ValidatorCaller(payload),
        ),
        result => result,
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.staking.add_validator'), { validator: id ? truncateAddress(String(id)) : '' }),
      title: t('task_center.group.staking'),
    });

    if (!isErr(outcome)) {
      return {
        message: '',
        success: outcome.value,
      };
    }

    if (!isActionable(outcome.error))
      return { message: '', success: false };

    logger.error(outcome.error.message);

    const cause = outcome.error.cause;
    const message: ValidationErrors | string = cause instanceof ApiValidationError
      ? cause.getValidationErrors(payload)
      : outcome.error.message;

    return { message, success: false };
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
      if (isRequestCancellation(error))
        return false;

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
