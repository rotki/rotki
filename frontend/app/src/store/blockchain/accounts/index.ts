import { Blockchain } from '@rotki/common/lib/blockchain';
import { useBlockchainAccountsApi } from '@/services/accounts';
import { BtcAccountData, GeneralAccountData } from '@/services/types-api';
import {
  AccountPayload,
  BasicBlockchainAccountPayload,
  BlockchainAccountPayload
} from '@/store/balances/types';
import { useBtcAccountsStore } from '@/store/blockchain/accounts/btc';
import { useChainsAccountsStore } from '@/store/blockchain/accounts/chains';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { BlockchainBalances } from '@/types/blockchain/balances';
import { BtcChains, isBtcChain, isRestChain } from '@/types/blockchain/chains';
import { BlockchainMetadata } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { logger } from '@/utils/logging';

export const useBlockchainAccountsStore = defineStore(
  'blockchain/accounts',
  () => {
    const {
      addBlockchainAccount,
      removeBlockchainAccount,
      editBlockchainAccount,
      editBtcAccount,
      queryAccounts,
      queryBtcAccounts
    } = useBlockchainAccountsApi();
    const { removeTag: removeBtcTag, update: updateBtc } =
      useBtcAccountsStore();
    const {
      removeTag: removeEthTag,
      updateEth,
      fetchEth2Validators
    } = useEthAccountsStore();
    const { removeTag: removeChainTag, update: updateChain } =
      useChainsAccountsStore();
    const { awaitTask } = useTasks();
    const { notify } = useNotifications();
    const { tc } = useI18n();

    const addAccount = async (
      blockchain: Blockchain,
      { address, label, tags, xpub }: AccountPayload
    ): Promise<string> => {
      const taskType = TaskType.ADD_ACCOUNT;
      const { taskId } = await addBlockchainAccount({
        blockchain,
        address,
        label,
        xpub,
        tags
      });

      const { result } = await awaitTask<string[], BlockchainMetadata>(
        taskId,
        taskType,
        {
          title: tc('actions.balances.blockchain_accounts_add.task.title', 0, {
            blockchain
          }),
          description: tc(
            'actions.balances.blockchain_accounts_add.task.description',
            0,
            { address }
          ),
          blockchain,
          numericKeys: []
        } as BlockchainMetadata,
        true
      );

      return result.length > 0 ? result[0] : '';
    };

    const editAccount = async (
      payload: BlockchainAccountPayload
    ): Promise<BtcAccountData | GeneralAccountData[]> => {
      const { blockchain } = payload;

      return [Blockchain.BTC, Blockchain.BCH].includes(blockchain)
        ? await editBtcAccount(payload)
        : await editBlockchainAccount(payload);
    };

    const removeAccount = async (payload: BasicBlockchainAccountPayload) => {
      const { accounts, blockchain } = payload;
      assert(accounts, 'Accounts was empty');
      const { taskId } = await removeBlockchainAccount(blockchain, accounts);
      try {
        const taskType = TaskType.REMOVE_ACCOUNT;
        await awaitTask<BlockchainBalances, BlockchainMetadata>(
          taskId,
          taskType,
          {
            title: tc(
              'actions.balances.blockchain_account_removal.task.title',
              0,
              {
                blockchain
              }
            ),
            description: tc(
              'actions.balances.blockchain_account_removal.task.description',
              0,
              { count: accounts.length }
            ),
            blockchain,
            numericKeys: []
          } as BlockchainMetadata
        );
      } catch (e: any) {
        logger.error(e);
        const title = tc(
          'actions.balances.blockchain_account_removal.error.title',
          0,
          {
            count: accounts.length,
            blockchain
          }
        );
        const description = tc(
          'actions.balances.blockchain_account_removal.error.description',
          0,
          {
            error: e.message
          }
        );
        notify({
          title,
          message: description,
          display: true
        });
      }
    };

    const fetchBlockchainAccounts = async (
      blockchain: Exclude<
        Blockchain,
        Blockchain.BTC | Blockchain.BCH | Blockchain.ETH2
      >
    ): Promise<string[] | null> => {
      try {
        const accounts = await queryAccounts(blockchain);
        if (blockchain === Blockchain.ETH) {
          updateEth(accounts);
        } else if (isRestChain(blockchain)) {
          updateChain(blockchain, accounts);
        }
        return accounts.map(account => account.address);
      } catch (e: any) {
        logger.error(e);
        notify({
          title: tc('actions.get_accounts.error.title'),
          message: tc('actions.get_accounts.error.description', 0, {
            blockchain: Blockchain[blockchain],
            message: e.message
          }),
          display: true
        });
        return null;
      }
    };

    const fetchBtcAccounts = async (chains: BtcChains): Promise<boolean> => {
      try {
        updateBtc(chains, await queryBtcAccounts(chains));
        return true;
      } catch (e: any) {
        logger.error(e);
        notify({
          title: tc('actions.get_accounts.error.title'),
          message: tc('actions.get_accounts.error.description', 0, {
            blockchain: Blockchain[chains],
            message: e.message
          }),
          display: true
        });
        return false;
      }
    };

    const fetch = async (blockchain: Blockchain) => {
      if (isBtcChain(blockchain)) {
        return fetchBtcAccounts(blockchain);
      } else if (isRestChain(blockchain) || blockchain === Blockchain.ETH) {
        return fetchBlockchainAccounts(blockchain);
      } else if (blockchain === Blockchain.ETH2) {
        return fetchEth2Validators();
      }
    };

    const removeTag = (tag: string) => {
      removeBtcTag(tag);
      removeEthTag(tag);
      removeChainTag(tag);
    };

    return {
      addAccount,
      editAccount,
      removeAccount,
      fetch,
      removeTag
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBlockchainAccountsStore, import.meta.hot)
  );
}
