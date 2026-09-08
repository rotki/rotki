import type { StateHandler } from '../interfaces';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { createStateHandler } from '@/modules/core/messaging/utils';

export function createRefreshBalancesHandler(): StateHandler {
  const { refreshBlockchainBalances } = useBlockchainBalances();

  return createStateHandler(async (data) => {
    await refreshBlockchainBalances({
      blockchain: data.blockchain,
    });
  });
}
