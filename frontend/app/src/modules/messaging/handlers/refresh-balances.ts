import type { StateHandler } from '../interfaces';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { createStateHandler } from '@/modules/messaging/utils';

export function createRefreshBalancesHandler(): StateHandler {
  // Capture functions at handler creation time (in setup context)
  const { fetchBlockchainBalances } = useBlockchainBalances();

  return createStateHandler(async (data) => {
    await fetchBlockchainBalances({
      blockchain: data.blockchain,
      ignoreCache: true,
    });
  });
}
