import type { MaybeRef } from 'vue';
import type {
  EthereumValidator,
  EthereumValidatorRequestPayload,
} from '@/modules/accounts/blockchain-accounts';
import type { BlockchainAssetBalances } from '@/modules/balances/types/blockchain-balances';
import type { Collection } from '@/modules/common/collection';
import { type Balance, type BigNumber, bigNumberify, Blockchain, Zero } from '@rotki/common';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { Module } from '@/modules/common/modules';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { isValidatorAccount } from '@/utils/blockchain/accounts/utils';
import { sortAndFilterValidators } from '@/utils/blockchain/accounts/validator';

export const useBlockchainValidatorsStore = defineStore('blockchain/validators', () => {
  const blockchainAccountsStore = useBlockchainAccountsStore();
  const { accounts } = storeToRefs(blockchainAccountsStore);
  const { updateAccounts } = blockchainAccountsStore;
  const balancesStore = useBalancesStore();
  const { balances } = storeToRefs(balancesStore);
  const { updateBalances } = balancesStore;

  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const isEth2Enabled = (): boolean => get(activeModules).includes(Module.ETH2);

  const stakingValidatorsLimits = ref<{
    limit: number;
    total: number;
  }>();

  const ethStakingValidators = computed<EthereumValidator[]>(() => {
    const accountData = get(accounts)[Blockchain.ETH2] ?? [];
    const accountBalances = get(balances)[Blockchain.ETH2] ?? [];

    const validators: EthereumValidator[] = [];
    for (const account of accountData.filter(isValidatorAccount)) {
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

  /**
   * Adjusts the balances for an ethereum staking validator based on the percentage of ownership.
   *
   * @param publicKey the validator's public key is used to identify the balance
   * @param newOwnershipPercentage the ownership percentage of the validator after the edit
   */
  const updateEthStakingOwnership = (publicKey: string, newOwnershipPercentage: BigNumber): void => {
    const validators = [...get(accounts)[Blockchain.ETH2]?.filter(isValidatorAccount) ?? []];
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
    fetchValidators,
    isEth2Enabled,
    stakingValidatorsLimits,
    updateEthStakingOwnership,
  };
});
