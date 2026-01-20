import type { MaybeRef } from 'vue';
import type {
  BlockchainAccount,
  EthereumValidator,
  EthereumValidatorRequestPayload,
  ValidatorData,
} from '@/types/blockchain/accounts';
import type { BlockchainAssetBalances } from '@/types/blockchain/balances';
import type { Collection } from '@/types/collection';
import { assert, type Balance, type BigNumber, bigNumberify, Blockchain, type EthValidatorFilter, Zero } from '@rotki/common';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { usePremium } from '@/composables/premium';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';
import { createValidatorAccount } from '@/utils/blockchain/accounts/create';
import { sortAndFilterValidators } from '@/utils/blockchain/accounts/validator';
import { logger } from '@/utils/logging';

export const useBlockchainValidatorsStore = defineStore('blockchain/validators', () => {
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const blockchainAccountsStore = useBlockchainAccountsStore();
  const { accounts } = storeToRefs(blockchainAccountsStore);
  const { updateAccounts } = blockchainAccountsStore;
  const balancesStore = useBalancesStore();
  const { balances } = storeToRefs(balancesStore);
  const { updateBalances } = balancesStore;

  const { getEth2Validators } = useBlockchainAccountsApi();
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const isEth2Enabled = (): boolean => get(activeModules).includes(Module.ETH2);
  const { getNativeAsset } = useSupportedChains();
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const stakingValidatorsLimits = ref<{
    limit: number;
    total: number;
  }>();

  const ethStakingValidators = computed<EthereumValidator[]>(() => {
    const accountData = get(accounts)[Blockchain.ETH2] ?? [];
    const accountBalances = get(balances)[Blockchain.ETH2] ?? [];

    const validators: EthereumValidator[] = [];
    for (const account of accountData) {
      assert(account.data.type === 'validator');
      const accountBalance: Balance = accountBalances[account.data.publicKey]?.assets?.ETH2?.address ?? {
        amount: Zero,
        value: Zero,
      };
      validators.push({
        ...account.data,
        ...accountBalance,
      });
    }

    return validators;
  });

  const fetchValidators = async (
    payload: MaybeRef<EthereumValidatorRequestPayload>,
  ): Promise<Collection<EthereumValidator>> => new Promise(
    (resolve) => {
      resolve(sortAndFilterValidators(
        get(ethStakingValidators),
        get(payload),
      ));
    },
  );

  const fetchEthStakingValidators = async (payload?: EthValidatorFilter): Promise<void> => {
    if (!isEth2Enabled())
      return;

    try {
      const validators = await getEth2Validators(payload);
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
        display: true,
        message: t('actions.get_accounts.error.description', {
          blockchain: Blockchain.ETH2,
          message: error.message,
        }),
        title: t('actions.get_accounts.error.title'),
      });
    }
  };

  const premium = usePremium();

  watch(premium, async () => {
    if (isEth2Enabled()) {
      await fetchEthStakingValidators({
        ignoreCache: true,
      });
      await fetchBlockchainBalances({
        blockchain: Blockchain.ETH2,
        ignoreCache: true,
      });
    }
  });

  /**
   * Adjusts the balances for an ethereum staking validator based on the percentage of ownership.
   *
   * @param publicKey the validator's public key is used to identify the balance
   * @param newOwnershipPercentage the ownership percentage of the validator after the edit
   */
  const updateEthStakingOwnership = (publicKey: string, newOwnershipPercentage: BigNumber): void => {
    const isValidator = (x: BlockchainAccount): x is BlockchainAccount<ValidatorData> => x.data.type === 'validator';
    const validators = [...get(accounts)[Blockchain.ETH2]?.filter(isValidator) ?? []];
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

    const { amount, value } = eth2[publicKey].assets[ETH2_ASSET].address;

    // we should not need to update anything if amount and value are zero
    if (amount.isZero() && value.isZero())
      return;

    const calc = (val: BigNumber, oldPercentage: BigNumber, newPercentage: BigNumber): BigNumber =>
      val.dividedBy(oldPercentage).multipliedBy(newPercentage);

    const newAmount = calc(amount, oldOwnershipPercentage, newOwnershipPercentage);

    const newValue = calc(value, oldOwnershipPercentage, newOwnershipPercentage);

    const updatedBalance: BlockchainAssetBalances = {
      [publicKey]: {
        assets: {
          [ETH2_ASSET]: {
            address: {
              amount: newAmount,
              value: newValue,
            },
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
    ethStakingValidators,
    fetchEthStakingValidators,
    fetchValidators,
    isEth2Enabled,
    stakingValidatorsLimits,
    updateEthStakingOwnership,
  };
});
