import type {
  AccountPayload,
  BlockchainAccount,
  DeleteBlockchainAccountParams,
  DeleteXpubParams,
  XpubAccountPayload,
} from '@/modules/accounts/blockchain-accounts';
import type { BlockchainBalances } from '@/modules/balances/types/blockchain-balances';
import type { EvmAccountsResult } from '@/modules/core/api/types/accounts';
import { Blockchain } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { convertBtcAccounts } from '@/modules/accounts/account-helpers';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { type BtcChains, isBtcChain } from '@/modules/core/common/chains';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

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

  const { submitTask } = useNativeTask();
  const { notifyError } = useNotifications();

  const { resetAddressNamesData } = useAddressNameResolution();
  const { t } = useI18n({ useScope: 'global' });
  const { getNativeAsset } = useSupportedChains();

  const addAccount = async (chain: string, payload: AccountPayload[] | XpubAccountPayload): Promise<string> => {
    const address = Array.isArray(payload) ? payload.map(item => item.address).join(',\n') : payload.xpub.xpub;
    // The address belongs in the id, not just the subtitle: `addMultipleAccounts` fans out over one
    // chain at parallelism 2, and `submitTask` dedups on id identity. A chain-only id collapses the
    // second address onto the first's promise, so it is reported added without ever being sent.
    const key = Array.isArray(payload) ? payload.map(item => item.address).join(',') : payload.xpub.xpub;
    const outcome = await submitTask<string[] | true>({
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.ADD, chain, key),
      kind: ActivityKind.ACCOUNTS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<string[] | true, TaskError>> => mapResult(
        await runTask<string[] | true>(
          async () => addBlockchainAccount(chain, payload),
        ),
        value => value,
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.accounts.add'), { address }),
      title: t('task_center.group.accounts'),
    });

    if (isErr(outcome)) {
      if (isActionable(outcome.error))
        throw new Error(outcome.error.message);
      return '';
    }

    const result = outcome.value;
    if (result === true) {
      return address;
    }

    return result.length > 0 ? result[0] : '';
  };

  const addEvmAccount = async ({ address, label, tags }: AccountPayload): Promise<EvmAccountsResult> => {
    const blockchain = 'EVM';
    const outcome = await submitTask<EvmAccountsResult>({
      // Same reasoning as `addAccount`: `addMultipleEvmAccounts` fans out over one pseudo-chain.
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.ADD, blockchain, address),
      kind: ActivityKind.ACCOUNTS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<EvmAccountsResult, TaskError>> => mapResult(
        await runTask<EvmAccountsResult>(
          async () => addEvmAccountCaller({ address, label, tags }),
        ),
        value => value,
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.accounts.add'), { address }),
      title: t('task_center.group.accounts'),
    });

    if (!isErr(outcome))
      return outcome.value;

    if (isErr(outcome) && isActionable(outcome.error))
      throw new Error(outcome.error.message);

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
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.REMOVE, chain),
      kind: ActivityKind.ACCOUNTS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BlockchainBalances>(
          async () => removeBlockchainAccount(chain, accounts),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.accounts.remove_count'), { count: accounts.length }, accounts.length),
      title: t('task_center.group.accounts'),
    });

    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      const title = t('actions.balances.blockchain_account_removal.error.title', {
        blockchain: chain,
        count: accounts.length,
      });
      const description = t('actions.balances.blockchain_account_removal.error.description', {
        error: outcome.error.message,
      });
      notifyError(title, description);
    }
  };

  const removeAgnosticAccount = async (chainType: string, address: string): Promise<void> => {
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.REMOVE, chainType),
      kind: ActivityKind.ACCOUNTS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BlockchainBalances>(
          async () => removeAgnosticBlockchainAccount(chainType, [address]),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.accounts.remove'), { address }),
      title: t('task_center.group.accounts'),
    });

    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      const title = t('actions.balances.blockchain_account_removal.agnostic.error.title', { address });
      const description = t('actions.balances.blockchain_account_removal.error.description', {
        error: outcome.error.message,
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
      if (isRequestCancellation(error))
        return null;

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
      if (isRequestCancellation(error))
        return false;

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
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.REMOVE, params.chain),
      kind: ActivityKind.ACCOUNTS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => deleteXpubCaller(params),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.accounts.remove_xpub'), { xpub: params.xpub }),
      title: t('task_center.group.accounts'),
    });

    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      const title = t('actions.balances.xpub_removal.error.title');
      const description = t('actions.balances.xpub_removal.error.description', {
        error: outcome.error.message,
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
