import { Blockchain } from '@rotki/common/lib/blockchain';
import { taskCancelledError } from '@/utils';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { type BlockchainBalances } from '@/types/blockchain/balances';
import {
  type BtcChains,
  isBtcChain,
  isRestChain
} from '@/types/blockchain/chains';
import { type BlockchainMetadata } from '@/types/task';
import { TaskType } from '@/types/task-type';
import {
  type AccountPayload,
  type BasicBlockchainAccountPayload,
  type BlockchainAccountPayload,
  type BtcAccountData,
  type GeneralAccountData
} from '@/types/blockchain/accounts';
import { type EvmAccountsResult } from '@/types/api/accounts';
import { type AddressBookSimplePayload } from '@/types/eth-names';

export const useBlockchainAccounts = () => {
  const {
    addBlockchainAccount,
    removeBlockchainAccount,
    editBlockchainAccount,
    editBtcAccount,
    queryAccounts,
    queryBtcAccounts,
    addEvmAccount: addEvmAccountCaller
  } = useBlockchainAccountsApi();
  const { removeTag: removeBtcTag, update: updateBtc } = useBtcAccountsStore();
  const {
    removeTag: removeEthTag,
    updateEth,
    fetchEth2Validators
  } = useEthAccountsStore();
  const { removeTag: removeChainTag, update: updateChain } =
    useChainsAccountsStore();
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();

  const { fetchEnsNames, resetAddressNamesData } = useAddressesNamesStore();
  const { t } = useI18n();

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

    try {
      const { result } = await awaitTask<string[], BlockchainMetadata>(
        taskId,
        taskType,
        {
          title: t('actions.balances.blockchain_accounts_add.task.title', {
            blockchain
          }),
          description: t(
            'actions.balances.blockchain_accounts_add.task.description',
            { address }
          ),
          blockchain
        },
        true
      );

      return result.length > 0 ? result[0] : '';
    } catch {
      return '';
    }
  };

  const addEvmAccount = async ({
    address,
    label,
    tags
  }: AccountPayload): Promise<EvmAccountsResult> => {
    const taskType = TaskType.ADD_ACCOUNT;
    const { taskId } = await addEvmAccountCaller({
      address,
      label,
      tags
    });

    try {
      const blockchain = 'EVM';
      const { result } = await awaitTask<EvmAccountsResult, BlockchainMetadata>(
        taskId,
        taskType,
        {
          title: t('actions.balances.blockchain_accounts_add.task.title', {
            blockchain
          }),
          description: t(
            'actions.balances.blockchain_accounts_add.task.description',
            { address }
          )
        },
        true
      );

      return snakeCaseTransformer(result);
    } catch {
      return {};
    }
  };

  const editAccount = async (
    payload: BlockchainAccountPayload
  ): Promise<BtcAccountData | GeneralAccountData[]> => {
    const { blockchain } = payload;

    if (isBtcChain(blockchain)) {
      return await editBtcAccount(payload);
    }
    const result = editBlockchainAccount(payload);
    resetAddressNamesData([payload]);
    return result;
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
          title: t('actions.balances.blockchain_account_removal.task.title', {
            blockchain
          }),
          description: t(
            'actions.balances.blockchain_account_removal.task.description',
            { count: accounts.length }
          ),
          blockchain
        }
      );
    } catch (e: any) {
      if (!taskCancelledError(e)) {
        logger.error(e);
        const title = t(
          'actions.balances.blockchain_account_removal.error.title',
          {
            count: accounts.length,
            blockchain
          }
        );
        const description = t(
          'actions.balances.blockchain_account_removal.error.description',
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
    }
  };

  const { isEvm } = useSupportedChains();

  const fetchBlockchainAccounts = async (
    blockchain: Exclude<
      Blockchain,
      Blockchain.BTC | Blockchain.BCH | Blockchain.ETH2
    >,
    refreshEns: boolean = false
  ): Promise<string[] | null> => {
    try {
      const accounts = await queryAccounts(blockchain);
      if (blockchain === Blockchain.ETH) {
        updateEth(accounts);
      } else if (isRestChain(blockchain)) {
        updateChain(blockchain, accounts);
      }

      if (isEvm(blockchain)) {
        const namesPayload: AddressBookSimplePayload[] = accounts.map(
          ({ address }) => ({
            address,
            blockchain
          })
        );

        startPromise(fetchEnsNames(namesPayload, refreshEns));
      }
      return accounts.map(account => account.address);
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.get_accounts.error.title'),
        message: t('actions.get_accounts.error.description', {
          blockchain: blockchain.toUpperCase(),
          message: e.message
        }),
        display: true
      });
      return null;
    }
  };

  const fetchBtcAccounts = async (chain: BtcChains): Promise<boolean> => {
    try {
      const accounts = await queryBtcAccounts(chain);
      updateBtc(chain, accounts);
      return true;
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.get_accounts.error.title'),
        message: t('actions.get_accounts.error.description', {
          blockchain: chain.toUpperCase(),
          message: e.message
        }),
        display: true
      });
      return false;
    }
  };

  const fetch = async (blockchain: Blockchain, refreshEns: boolean = false) => {
    if (isBtcChain(blockchain)) {
      return fetchBtcAccounts(blockchain);
    } else if (isRestChain(blockchain) || blockchain === Blockchain.ETH) {
      return fetchBlockchainAccounts(blockchain, refreshEns);
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
    addEvmAccount,
    editAccount,
    removeAccount,
    fetch,
    removeTag
  };
};
