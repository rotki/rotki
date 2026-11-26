import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { ActionStatus } from '@/modules/core/common/action';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { validatorAddActivity, validatorAddLabel } from '@/modules/staking/staking.activity';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseEthValidatorAdditionReturn {
  addEth2Validator: (payload: Eth2Validator) => Promise<ActionStatus<ValidationErrors | string>>;
}

/**
 * Adds an ETH2 validator as a task-center activity.
 *
 * @remarks
 * Refuses up front when the ETH2 module is disabled. A rejected addition reports the backend's
 * field-level errors when it carries an {@link ApiValidationError}, its message otherwise, and an
 * empty message when it was cancelled.
 */
export function useEthValidatorAddition(): UseEthValidatorAdditionReturn {
  const { addEth2Validator: addEth2ValidatorCaller } = useBlockchainAccountsApi();
  const { isEth2Enabled } = useBlockchainValidatorsStore();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  const addEth2Validator = async (payload: Eth2Validator): Promise<ActionStatus<ValidationErrors | string>> => {
    if (!isEth2Enabled()) {
      return {
        message: '',
        success: false,
      };
    }
    const outcome = await submitTask<boolean>({
      id: validatorAddActivity.id(payload),
      kind: validatorAddActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => addEth2ValidatorCaller(payload),
        ),
        result => result,
      ),
      subtitle: validatorAddLabel(payload),
      title: t('task_center.group.staking'),
      userStarted: true,
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

  return { addEth2Validator };
}
