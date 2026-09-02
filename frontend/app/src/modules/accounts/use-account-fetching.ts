import { Blockchain } from '@rotki/common';
import { convertBtcAccounts } from '@/modules/accounts/account-helpers';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { isSessionExpired } from '@/modules/core/api/response-handlers';
import { type BtcChains, isBtcChain } from '@/modules/core/common/chains';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseAccountFetchingReturn {
  fetch: (blockchain: string) => Promise<void>;
}

export function useAccountFetching(): UseAccountFetchingReturn {
  const { queryAccounts, queryBtcAccounts } = useBlockchainAccountsApi();
  const { fetchEthStakingValidators } = useEthStaking();
  const { revisionOf, updateAccounts } = useBlockchainAccountsStore();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { getNativeAsset } = useSupportedChains();

  /**
   * Reports a chain's fetch failure, unless it is one the user should not be told about.
   *
   * @remarks
   * This fans out over every supported chain, so a logout mid-flight would otherwise raise one
   * "no user is currently logged in" per chain. A cancelled request is likewise the queue dropping
   * work the user moved away from. Everything else is surfaced.
   */
  const notifyFetchFailure = (chain: string, error: unknown): void => {
    if (isRequestCancellation(error) || isSessionExpired(error))
      return;

    logger.error(error);
    notifyError(
      t('actions.get_accounts.error.title'),
      t('actions.get_accounts.error.description', {
        blockchain: chain.toUpperCase(),
        message: getErrorMessage(error),
      }),
    );
  };

  const fetchBlockchainAccounts = async (chain: string): Promise<void> => {
    const revision = revisionOf(chain);
    try {
      const accounts = await queryAccounts(chain);
      if (revisionOf(chain) !== revision)
        return;

      const chainInfo = {
        chain,
        nativeAsset: getNativeAsset(chain),
      };

      updateAccounts(chain, accounts.map(account => createAccount(account, chainInfo)));
    }
    catch (error: unknown) {
      notifyFetchFailure(chain, error);
    }
  };

  const fetchBtcAccounts = async (chain: BtcChains): Promise<void> => {
    const revision = revisionOf(chain);
    try {
      const accounts = await queryBtcAccounts(chain);
      if (revisionOf(chain) !== revision)
        return;

      updateAccounts(chain, convertBtcAccounts(getNativeAsset, chain, accounts));
    }
    catch (error: unknown) {
      notifyFetchFailure(chain, error);
    }
  };

  const fetch = async (blockchain: string): Promise<void> => {
    if (isBtcChain(blockchain))
      await fetchBtcAccounts(blockchain);
    else if (blockchain === Blockchain.ETH2)
      await fetchEthStakingValidators();
    else
      await fetchBlockchainAccounts(blockchain);
  };

  return { fetch };
}
