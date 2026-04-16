import type {
  AccountPayload,
  BlockchainAccount,
  DeleteBlockchainAccountParams,
  DeleteXpubParams,
  XpubAccountPayload,
} from '@/modules/accounts/blockchain-accounts';
import type { EvmAccountsResult } from '@/modules/api/types/accounts';
import type { BlockchainBalances } from '@/modules/balances/types/blockchain-balances';
import type { BlockchainMetadata } from '@/modules/tasks/types';
import { Blockchain } from '@rotki/common';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { convertBtcAccounts } from '@/modules/accounts/account-helpers';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { logger } from '@/modules/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { type BtcChains, isBtcChain } from '@/modules/onchain/chains';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';

interface UseBlockchainAccountsReturn {
  addAccount: (chain: string, payload: AccountPayload[] | XpubAccountPayload) => Promise<string>;
  addEvmAccount: ({ address, label, tags }: AccountPayload) => Promise<EvmAccountsResult>;
  editAccount: (payload: AccountPayload | XpubAccountPayload, chain: string) => Promise<BlockchainAccount[]>;
  editAgnosticAccount: (chainType: string, payload: AccountPayload) => Promise<boolean>;
  removeAccount: (payload: DeleteBlockchainAccountParams) => Promise<void>;
  removeAgnosticAccount: (chainType: string, address: string) => Promise<void>;
  fetch: (blockchain: string) => Promise<void>;
  deleteXpub: (params: DeleteXpubParams) => Promise<void>;
}

export function useBlockchainAccounts(): UseBlockchainAccountsReturn {
  const {
    addBlockchainAccount,
    addEvmAccount: addEvmAccountCaller,
    editAgnosticBlockchainAccount,
    editBlockchainAccount,
    editBtcAccount,
    queryAccounts,
    queryBtcAccounts,
    removeAgnosticBlockchainAccount,
    removeBlockchainAccount,
  } = useBlockchainAccountsApi();
  const { deleteXpub: deleteXpubCaller } = useBlockchainAccountsApi();
  const { fetchEthStakingValidators } = useEthStaking();
  const { updateAccounts } = useBlockchainAccountsStore();

  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();

  const { resetAddressNamesData } = useAddressNameResolution();
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName, getNativeAsset } = useSupportedChains();

  const addAccount = async (chain: string, payload: AccountPayload[] | XpubAccountPayload): Promise<string> => {
    const address = Array.isArray(payload) ? payload.map(item => item.address).join(',\n') : payload.xpub.xpub;
    const outcome = await runTask<string[] | true, BlockchainMetadata>(
      async () => addBlockchainAccount(chain, payload),
      {
        type: TaskType.ADD_ACCOUNT,
        meta: {
          blockchain: chain,
          description: t('actions.balances.blockchain_accounts_add.task.description', { address }),
          title: t('actions.balances.blockchain_accounts_add.task.title', { blockchain: getChainName(chain) }),
        },
        unique: false,
      },
    );

    if (!outcome.success) {
      if (isActionableFailure(outcome))
        throw new Error(outcome.message);
      return '';
    }

    if (outcome.result === true) {
      return address;
    }

    return outcome.result.length > 0 ? outcome.result[0] : '';
  };

  const addEvmAccount = async ({ address, label, tags }: AccountPayload): Promise<EvmAccountsResult> => {
    const blockchain = 'EVM';
    const outcome = await runTask<EvmAccountsResult, BlockchainMetadata>(
      async () => addEvmAccountCaller({ address, label, tags }),
      {
        type: TaskType.ADD_ACCOUNT,
        meta: {
          description: t('actions.balances.blockchain_accounts_add.task.description', { address }),
          title: t('actions.balances.blockchain_accounts_add.task.title', { blockchain }),
        },
        unique: false,
      },
    );

    if (outcome.success)
      return outcome.result;

    if (isActionableFailure(outcome))
      throw new Error(outcome.message);

    return {};
  };

  const resetAddressesData = (chain: string | null, payload: AccountPayload): void => {
    try {
      const addressBookPayload = {
        address: payload.address,
        blockchain: chain,
      };

      resetAddressNamesData([
        addressBookPayload,
      ]);
    }
    catch (error: unknown) {
      logger.error(error);
    }
  };

  const editAccount = async (
    payload: AccountPayload | XpubAccountPayload,
    chain: string,
  ): Promise<BlockchainAccount[]> => {
    if (isBtcChain(chain) || 'xpub' in payload) {
      const response = convertBtcAccounts(getNativeAsset, chain, await editBtcAccount(payload, chain));

      if (!('xpub' in payload))
        resetAddressesData(chain, payload);

      return response;
    }

    const result = await editBlockchainAccount(payload, chain);

    resetAddressesData(chain, payload);

    const chainInfo = {
      chain,
      nativeAsset: getNativeAsset(chain),
    };

    return result.map(account => createAccount(account, chainInfo));
  };

  const editAgnosticAccount = async (chainType: string, payload: AccountPayload): Promise<boolean> => {
    const result = await editAgnosticBlockchainAccount(chainType, payload);
    resetAddressesData(null, payload);
    return result;
  };

  const removeAccount = async (payload: DeleteBlockchainAccountParams): Promise<void> => {
    const { accounts, chain } = payload;
    const outcome = await runTask<BlockchainBalances, BlockchainMetadata>(
      async () => removeBlockchainAccount(chain, accounts),
      {
        type: TaskType.REMOVE_ACCOUNT,
        meta: {
          blockchain: chain,
          description: t('actions.balances.blockchain_account_removal.task.description', { count: accounts.length }),
          title: t('actions.balances.blockchain_account_removal.task.title', { blockchain: chain }),
        },
      },
    );

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      const title = t('actions.balances.blockchain_account_removal.error.title', {
        blockchain: chain,
        count: accounts.length,
      });
      const description = t('actions.balances.blockchain_account_removal.error.description', {
        error: outcome.message,
      });
      notifyError(title, description);
    }
  };

  const removeAgnosticAccount = async (chainType: string, address: string): Promise<void> => {
    const outcome = await runTask<BlockchainBalances, BlockchainMetadata>(
      async () => removeAgnosticBlockchainAccount(chainType, [address]),
      {
        type: TaskType.REMOVE_ACCOUNT,
        meta: {
          description: t('actions.balances.blockchain_account_removal.agnostic.task.description', { address }),
          title: t('actions.balances.blockchain_account_removal.agnostic.task.title'),
        },
      },
    );

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      const title = t('actions.balances.blockchain_account_removal.agnostic.error.title', { address });
      const description = t('actions.balances.blockchain_account_removal.error.description', {
        error: outcome.message,
      });
      notifyError(title, description);
    }
  };

  const fetchBlockchainAccounts = async (chain: string): Promise<string[] | null> => {
    try {
      const accounts = await queryAccounts(chain);
      const chainInfo = {
        chain,
        nativeAsset: getNativeAsset(chain),
      };

      updateAccounts(
        chain,
        accounts.map(account => createAccount(account, chainInfo)),
      );
      return accounts.map(account => account.address);
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(
        t('actions.get_accounts.error.title'),
        t('actions.get_accounts.error.description', {
          blockchain: chain.toUpperCase(),
          message: getErrorMessage(error),
        }),
      );
      return null;
    }
  };

  const fetchBtcAccounts = async (chain: BtcChains): Promise<boolean> => {
    try {
      const accounts = await queryBtcAccounts(chain);
      updateAccounts(chain, convertBtcAccounts(getNativeAsset, chain, accounts));
      return true;
    }
    catch (error: unknown) {
      logger.error(error);
      notifyError(
        t('actions.get_accounts.error.title'),
        t('actions.get_accounts.error.description', {
          blockchain: chain.toUpperCase(),
          message: getErrorMessage(error),
        }),
      );
      return false;
    }
  };

  const deleteXpub = async (params: DeleteXpubParams): Promise<void> => {
    const outcome = await runTask<boolean, BlockchainMetadata>(
      async () => deleteXpubCaller(params),
      {
        type: TaskType.REMOVE_ACCOUNT,
        meta: {
          blockchain: params.chain,
          description: t('actions.balances.xpub_removal.task.description', { xpub: params.xpub }),
          title: t('actions.balances.xpub_removal.task.title'),
        },
      },
    );

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      const title = t('actions.balances.xpub_removal.error.title');
      const description = t('actions.balances.xpub_removal.error.description', {
        error: outcome.message,
        xpub: params.xpub,
      });
      notifyError(title, description);
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

  return {
    addAccount,
    addEvmAccount,
    deleteXpub,
    editAccount,
    editAgnosticAccount,
    fetch,
    removeAccount,
    removeAgnosticAccount,
  };
}
