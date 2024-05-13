import { Blockchain } from '@rotki/common/lib/blockchain';
import { type BtcChains, isBtcChain } from '@/types/blockchain/chains';
import { TaskType } from '@/types/task-type';
import type {
  AccountPayload,
  BtcAccountData,
  DeleteBlockchainAccountParams,
  DeleteXpubParams,
  GeneralAccountData,
  XpubAccountPayload,
} from '@/types/blockchain/accounts';
import type { BlockchainBalances } from '@/types/blockchain/balances';
import type { BlockchainMetadata } from '@/types/task';
import type { EvmAccountsResult } from '@/types/api/accounts';

export function useBlockchainAccounts() {
  const {
    addBlockchainAccount,
    removeBlockchainAccount,
    editBlockchainAccount,
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

  const { resetAddressNamesData } = useAddressesNamesStore();
  const { t } = useI18n();
  const { getNativeAsset } = useSupportedChains();

  const addAccount = async (
    chain: string,
    payload: AccountPayload[] | XpubAccountPayload,
  ): Promise<string> => {
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

  const addEvmAccount = async ({
    address,
    label,
    tags,
  }: AccountPayload): Promise<EvmAccountsResult> => {
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
          description: t(
            'actions.balances.blockchain_accounts_add.task.description',
            { address },
          ),
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

  const editAccount = async (
    payload: AccountPayload | XpubAccountPayload,
    chain: string,
  ): Promise<BtcAccountData | GeneralAccountData[]> => {
    if (isBtcChain(chain) || 'xpub' in payload)
      return await editBtcAccount(payload, chain);

    const result = editBlockchainAccount(payload, chain);
    resetAddressNamesData([{
      ...payload,
      blockchain: chain,
    }]);
    return result;
  };

  const removeAccount = async (payload: DeleteBlockchainAccountParams) => {
    const { accounts, chain } = payload;
    const { taskId } = await removeBlockchainAccount(chain, accounts);
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      await awaitTask<BlockchainBalances, BlockchainMetadata>(
        taskId,
        taskType,
        {
          title: t('actions.balances.blockchain_account_removal.task.title', {
            blockchain: chain,
          }),
          description: t(
            'actions.balances.blockchain_account_removal.task.description',
            { count: accounts.length },
          ),
          blockchain: chain,
        },
      );
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        const title = t(
          'actions.balances.blockchain_account_removal.error.title',
          {
            count: accounts.length,
            blockchain: chain,
          },
        );
        const description = t(
          'actions.balances.blockchain_account_removal.error.description',
          {
            error: error.message,
          },
        );
        notify({
          title,
          message: description,
          display: true,
        });
      }
    }
  };

  const fetchBlockchainAccounts = async (
    chain: string,
  ): Promise<string[] | null> => {
    try {
      const accounts = await queryAccounts(chain);
      const chainInfo = {
        nativeAsset: getNativeAsset(chain),
        chain,
      };

      updateAccounts(chain, accounts.map(account => createAccount(account, chainInfo)));
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

  const deleteXpub = async (params: DeleteXpubParams) => {
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
        const description = t(
          'actions.balances.xpub_removal.error.description',
          {
            xpub: params.xpub,
            error: error.message,
          },
        );
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
    removeAccount,
    fetch,
    deleteXpub,
    removeTag,
  };
}
