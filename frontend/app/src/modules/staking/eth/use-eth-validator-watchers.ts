import { Blockchain } from '@rotki/common';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { usePremium } from '@/modules/premium/use-premium';
import { useEthValidatorFetching } from '@/modules/staking/eth/use-eth-validator-fetching';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

export function useEthValidatorWatchers(): void {
  const { isEth2Enabled } = useBlockchainValidatorsStore();
  const { fetchEthStakingValidators } = useEthValidatorFetching();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const premium = usePremium();

  watch(premium, async () => {
    if (isEth2Enabled()) {
      await fetchEthStakingValidators({
        ignoreCache: true,
      });
      await refreshBlockchainBalances({
        blockchain: Blockchain.ETH2,
      });
    }
  });
}
