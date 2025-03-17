import type { EvmAccountsResult } from '@/types/api/accounts';
import type {
  AccountPayload,
  BlockchainAccount,
  DeleteBlockchainAccountParams,
  DeleteXpubParams,
  XpubAccountPayload,
} from '@/types/blockchain/accounts';
import type { BlockchainBalances } from '@/types/blockchain/balances';
import type { BlockchainMetadata } from '@/types/task';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainStore } from '@/store/blockchain';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { type BtcChains, isBtcChain } from '@/types/blockchain/chains';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { convertBtcAccounts } from '@/utils/blockchain/accounts';
import { createAccount } from '@/utils/blockchain/accounts/create';
import { logger } from '@/utils/logging';
import { Blockchain } from '@rotki/common';

interface UseBlockchainAccountsReturn {
  addAccount: (chain: string, payload: AccountPayload[] | XpubAccountPayload) => Promise<string>;
  addEvmAccount: ({ address, label, tags }: AccountPayload) => Promise<EvmAccountsResult>;
  editAccount: (payload: AccountPayload | XpubAccountPayload, chain: string) => Promise<BlockchainAccount[]>;
  editAgnosticAccount: (chainType: string, payload: AccountPayload) => Promise<boolean>;
  removeAccount: (payload: DeleteBlockchainAccountParams) => Promise<void>;
  removeAgnosticAccount: (chainType: string, address: string) => Promise<void>;
  fetch: (blockchain: string) => Promise<void>;
  deleteXpub: (params: DeleteXpubParams) => Promise<void>;
  removeTag: (tag: string) => void;
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
  const { removeTag, updateAccounts } = useBlockchainStore();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();

  const { resetAddressNamesData } = useAddressesNamesStore();
  const { t } = useI18n();
  const { getChainName, getNativeAsset } = useSupportedChains();

  const addAccount = async (chain: string, payload: AccountPayload[] | XpubAccountPayload): Promise<string> => {
    const taskType = TaskType.ADD_ACCOUNT;
    const { taskId } = await addBlockchainAccount(chain, payload);

    const address = Array.isArray(payload) ? payload.map(item => item.address).join(',\n') : payload.xpub.xpub;
    const { result } = await awaitTask<string[], BlockchainMetadata>(
      taskId,
      taskType,
      {
        blockchain: chain,
        description: t('actions.balances.blockchain_accounts_add.task.description', { address }),
        title: t('actions.balances.blockchain_accounts_add.task.title', { blockchain: get(getChainName(chain)) }),
      },
      true,
    );

    return result.length > 0 ? result[0] : '';
  };

  const addEvmAccount = async ({ address, label, tags }: AccountPayload): Promise<EvmAccountsResult> => {
    const taskType = TaskType.ADD_ACCOUNT;
    const { taskId } = await addEvmAccountCaller({
      address,
      label,
      tags,
    });

    try {
      const blockchain = 'EVM';
      const { result } = await awaitTask<EvmAccountsResult, BlockchainMetadata>(
        taskId,
        taskType,
        {
          description: t('actions.balances.blockchain_accounts_add.task.description', { address }),
          title: t('actions.balances.blockchain_accounts_add.task.title', {
            blockchain,
          }),
        },
        true,
      );

      return result;
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        throw error;
      return {};
    }
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
    catch (error: any) {
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
    const { taskId } = await removeBlockchainAccount(chain, accounts);
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      await awaitTask<BlockchainBalances, BlockchainMetadata>(taskId, taskType, {
        blockchain: chain,
        description: t('actions.balances.blockchain_account_removal.task.description', { count: accounts.length }),
        title: t('actions.balances.blockchain_account_removal.task.title', {
          blockchain: chain,
        }),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const title = t('actions.balances.blockchain_account_removal.error.title', {
          blockchain: chain,
          count: accounts.length,
        });
        const description = t('actions.balances.blockchain_account_removal.error.description', {
          error: error.message,
        });
        notify({
          display: true,
          message: description,
          title,
        });
      }
    }
  };

  const removeAgnosticAccount = async (chainType: string, address: string): Promise<void> => {
    const { taskId } = await removeAgnosticBlockchainAccount(chainType, [address]);
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      await awaitTask<BlockchainBalances, BlockchainMetadata>(taskId, taskType, {
        description: t('actions.balances.blockchain_account_removal.agnostic.task.description', { address }),
        title: t('actions.balances.blockchain_account_removal.agnostic.task.title'),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const title = t('actions.balances.blockchain_account_removal.agnostic.error.title', {
          address,
        });
        const description = t('actions.balances.blockchain_account_removal.error.description', {
          error: error.message,
        });
        notify({
          display: true,
          message: description,
          title,
        });
      }
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
    catch (error: any) {
      logger.error(error);
      notify({
        display: true,
        message: t('actions.get_accounts.error.description', {
          blockchain: chain.toUpperCase(),
          message: error.message,
        }),
        title: t('actions.get_accounts.error.title'),
      });
      return null;
    }
  };

  const fetchBtcAccounts = async (chain: BtcChains): Promise<boolean> => {
    try {
      const accounts = await queryBtcAccounts(chain);
      updateAccounts(chain, convertBtcAccounts(getNativeAsset, chain, accounts));
      return true;
    }
    catch (error: any) {
      logger.error(error);
      notify({
        display: true,
        message: t('actions.get_accounts.error.description', {
          blockchain: chain.toUpperCase(),
          message: error.message,
        }),
        title: t('actions.get_accounts.error.title'),
      });
      return false;
    }
  };

  const deleteXpub = async (params: DeleteXpubParams): Promise<void> => {
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      if (isTaskRunning(taskType))
        return;

      const { taskId } = await deleteXpubCaller(params);
      await awaitTask<boolean, BlockchainMetadata>(taskId, taskType, {
        blockchain: params.chain,
        description: t('actions.balances.xpub_removal.task.description', {
          xpub: params.xpub,
        }),
        title: t('actions.balances.xpub_removal.task.title'),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const title = t('actions.balances.xpub_removal.error.title');
        const description = t('actions.balances.xpub_removal.error.description', {
          error: error.message,
          xpub: params.xpub,
        });
        notify({
          display: true,
          message: description,
          title,
        });
      }
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
    removeTag,
  };
}
