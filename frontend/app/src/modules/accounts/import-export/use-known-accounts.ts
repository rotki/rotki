import { Blockchain } from '@rotki/common';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { getChainType } from '@/modules/accounts/import-export/account-csv-schema';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

/** An address already tracked, under the chain a CSV row would name it with. */
interface KnownAccount {
  address: string;
  chain: string;
}

interface UseKnownAccountsReturn {
  getKnownAccounts: () => KnownAccount[];
}

/**
 * Lists the accounts and staking validators already tracked, keyed the way an imported CSV row is,
 * so the import can tell which rows it can skip.
 */
export function useKnownAccounts(): UseKnownAccountsReturn {
  const { isEvmCompatible } = useSupportedChains();
  const { getAccounts } = useBlockchainAccountData();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

  function getKnownAccounts(): KnownAccount[] {
    return getAccounts().map(group => ({
      address: getAccountAddress(group),
      chain: getChainType(group.chains, isEvmCompatible),
    })).concat(get(ethStakingValidators).map(validator => ({
      address: validator.publicKey,
      chain: Blockchain.ETH2,
    })));
  }

  return {
    getKnownAccounts,
  };
}
