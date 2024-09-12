import { Blockchain } from '@rotki/common';
import { type BtcChains, isBtcChain } from '@/types/blockchain/chains';
import { TaskType } from '@/types/task-type';
import type {
  AccountPayload,
  BlockchainAccount,
  DeleteBlockchainAccountParams,
  DeleteXpubParams,
  XpubAccountPayload,
} from '@/types/blockchain/accounts';
import type { BlockchainBalances } from '@/types/blockchain/balances';
import type { BlockchainMetadata } from '@/types/task';
import type { EvmAccountsResult } from '@/types/api/accounts';

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
    removeBlockchainAccount,
    removeAgnosticBlockchainAccount,
    editBlockchainAccount,
    editAgnosticBlockchainAccount,
    editBtcAccount,
    queryAccounts,
    queryBtcAccounts,
    addEvmAccount: addEvmAccountCaller,
  } = useBlockchainAccountsApi();
  const { deleteXpub: deleteXpubCaller } = useBlockchainAccountsApi();
  const { fetchEthStakingValidators } = useEthStaking();
  const { updateAccounts, removeTag } = useBlockchainStore();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();

  const { resetAddressNamesData, deleteAddressBook } = useAddressesNamesStore();
  const { t } = useI18n();
  const { getNativeAsset } = useSupportedChains();

  const addAccount = async (chain: string, payload: AccountPayload[] | XpubAccountPayload): Promise<string> => {
    const taskType = TaskType.ADD_ACCOUNT;
    const { taskId } = await addBlockchainAccount(chain, payload);

    const address = Array.isArray(payload) ? payload.map(item => item.address).join(',\n') : payload.xpub;
    const { result } = await awaitTask<string[], BlockchainMetadata>(
      taskId,
      taskType,
      {
        title: t('actions.balances.blockchain_accounts_add.task.title', { blockchain: chain }),
        description: t('actions.balances.blockchain_accounts_add.task.description', { address }),
        blockchain: chain,
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
          title: t('actions.balances.blockchain_accounts_add.task.title', {
            blockchain,
          }),
          description: t('actions.balances.blockchain_accounts_add.task.description', { address }),
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

  const resetAddressesData = async (chain: string | null, payload: AccountPayload): Promise<void> => {
    try {
      const addressBookPayload = {
        address: payload.address,
        blockchain: chain,
      };

      if (!payload.label) {
        await deleteAddressBook('private', [addressBookPayload]);
      }
      else {
        resetAddressNamesData([
          addressBookPayload,
        ]);
      }
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
        await resetAddressesData(chain, payload);

      return response;
    }

    const result = await editBlockchainAccount(payload, chain);

    await resetAddressesData(chain, payload);

    const chainInfo = {
      nativeAsset: getNativeAsset(chain),
      chain,
    };

    return result.map(account => createAccount(account, chainInfo));
  };

  const editAgnosticAccount = async (chainType: string, payload: AccountPayload): Promise<boolean> => {
    const result = await editAgnosticBlockchainAccount(chainType, payload);
    await resetAddressesData(null, payload);
    return result;
  };

  const removeAccount = async (payload: DeleteBlockchainAccountParams): Promise<void> => {
    const { accounts, chain } = payload;
    const { taskId } = await removeBlockchainAccount(chain, accounts);
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      await awaitTask<BlockchainBalances, BlockchainMetadata>(taskId, taskType, {
        title: t('actions.balances.blockchain_account_removal.task.title', {
          blockchain: chain,
        }),
        description: t('actions.balances.blockchain_account_removal.task.description', { count: accounts.length }),
        blockchain: chain,
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const title = t('actions.balances.blockchain_account_removal.error.title', {
          count: accounts.length,
          blockchain: chain,
        });
        const description = t('actions.balances.blockchain_account_removal.error.description', {
          error: error.message,
        });
        notify({
          title,
          message: description,
          display: true,
        });
      }
    }
  };

  const removeAgnosticAccount = async (chainType: string, address: string): Promise<void> => {
    const { taskId } = await removeAgnosticBlockchainAccount(chainType, [address]);
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      await awaitTask<BlockchainBalances, BlockchainMetadata>(taskId, taskType, {
        title: t('actions.balances.blockchain_account_removal.agnostic.task.title'),
        description: t('actions.balances.blockchain_account_removal.agnostic.task.description', { address }),
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
          title,
          message: description,
          display: true,
        });
      }
    }
  };

  const fetchBlockchainAccounts = async (chain: string): Promise<string[] | null> => {
    try {
      const accounts = await queryAccounts(chain);
      const chainInfo = {
        nativeAsset: getNativeAsset(chain),
        chain,
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
        title: t('actions.get_accounts.error.title'),
        message: t('actions.get_accounts.error.description', {
          blockchain: chain.toUpperCase(),
          message: error.message,
        }),
        display: true,
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
        title: t('actions.get_accounts.error.title'),
        message: t('actions.get_accounts.error.description', {
          blockchain: chain.toUpperCase(),
          message: error.message,
        }),
        display: true,
      });
      return false;
    }
  };

  const deleteXpub = async (params: DeleteXpubParams): Promise<void> => {
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      if (get(isTaskRunning(taskType)))
        return;

      const { taskId } = await deleteXpubCaller(params);
      await awaitTask<boolean, BlockchainMetadata>(taskId, taskType, {
        title: t('actions.balances.xpub_removal.task.title'),
        description: t('actions.balances.xpub_removal.task.description', {
          xpub: params.xpub,
        }),
        blockchain: params.chain,
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const title = t('actions.balances.xpub_removal.error.title');
        const description = t('actions.balances.xpub_removal.error.description', {
          xpub: params.xpub,
          error: error.message,
        });
        notify({
          title,
          message: description,
          display: true,
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
    editAccount,
    editAgnosticAccount,
    removeAccount,
    removeAgnosticAccount,
    fetch,
    deleteXpub,
    removeTag,
  };
}
