import { type BigNumber, Blockchain } from '@rotki/common';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { Section } from '@/types/status';
import { Module } from '@/types/modules';
import type { BlockchainAccount, ValidatorData } from '@/types/blockchain/accounts';
import type { Eth2Validator } from '@/types/balances';
import type { ActionStatus } from '@/types/action';
import type { TaskMeta } from '@/types/task';

export function useEthStaking() {
  const {
    getEth2Validators,
    addEth2Validator: addEth2ValidatorCaller,
    editEth2Validator: editEth2ValidatorCaller,
    deleteEth2Validators: deleteEth2ValidatorsCaller,
  } = useBlockchainAccountsApi();
  const blockchainStore = useBlockchainStore();
  const { updateAccounts, getAccounts, updateBalances } = blockchainStore;
  const { stakingValidatorsLimits, ethStakingValidators, balances } = storeToRefs(blockchainStore);
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { setMessage } = useMessageStore();
  const { t } = useI18n();
  const { resetStatus } = useStatusUpdater(Section.STAKING_ETH2);
  const { getNativeAsset } = useSupportedChains();

  const isEth2Enabled = () => get(activeModules).includes(Module.ETH2);

  const fetchEthStakingValidators = async () => {
    if (!isEth2Enabled())
      return;

    try {
      const validators = await getEth2Validators();
      updateAccounts(
        Blockchain.ETH2,
        validators.entries.map(validator =>
          createValidatorAccount(validator, {
            chain: Blockchain.ETH2,
            nativeAsset: getNativeAsset(Blockchain.ETH2),
          }),
        ),
      );
      set(stakingValidatorsLimits, { limit: validators.entriesLimit, total: validators.entriesFound });
    }
    catch (error: any) {
      logger.error(error);
      notify({
        title: t('actions.get_accounts.error.title'),
        message: t('actions.get_accounts.error.description', {
          blockchain: Blockchain.ETH2,
          message: error.message,
        }),
        display: true,
      });
    }
  };

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
        const remainingValidators = getAccounts(Blockchain.ETH2).filter(
          ({ data }) => 'publicKey' in data && !validators.includes(data.publicKey),
        );
        updateAccounts(Blockchain.ETH2, remainingValidators);
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

    const { eth2 } = get(balances);
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

  return {
    fetchEthStakingValidators,
    addEth2Validator,
    editEth2Validator,
    deleteEth2Validators,
    updateEthStakingOwnership,
  };
}
