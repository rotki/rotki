import type { EthereumValidator, ValidatorAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type Ref } from 'vue';
import { isValidatorAccount } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

interface UseEthStakingValidatorOptionsReturn {
  ethStakingValidators: Ref<EthereumValidator[]>;
  withdrawalAddressOptions: ComputedRef<string[]>;
  hasNoValidators: ComputedRef<boolean>;
}

export function useEthStakingValidatorOptions(): UseEthStakingValidatorOptionsReturn {
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

  const eth2Accounts = computed(() => get(accountsPerChain)[Blockchain.ETH2] ?? []);

  const validatorAccounts = computed<ValidatorAccount[]>(() =>
    get(eth2Accounts).filter(isValidatorAccount),
  );

  const withdrawalAddressOptions = computed<string[]>(() => {
    const addresses = new Set<string>();
    for (const account of get(validatorAccounts)) {
      if (account.withdrawalAddress)
        addresses.add(account.withdrawalAddress);
    }
    return [...addresses];
  });

  const hasNoValidators = computed<boolean>(() => get(eth2Accounts).length === 0);

  return {
    ethStakingValidators,
    hasNoValidators,
    withdrawalAddressOptions,
  };
}
