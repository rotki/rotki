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
import { err, flatMap as flatMapResult, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { convertBtcAccounts } from '@/modules/accounts/account-helpers';
import { accountActivityLabel, accountAddActivity, accountRemoveActivity, type AccountSubject, accountTargetOf, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
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
import { isActionable, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseBlockchainAccountsReturn {
  /**
   * The added address on success. Failure stays a value: `TaskError` distinguishes a cancelled
   * add from a failed one, which a bare string could not.
   */
  addAccount: (chain: string, payload: AccountPayload[] | XpubAccountPayload) => Promise<Result<string, TaskError>>;
  addEvmAccount: ({ address, label, tags }: AccountPayload) => Promise<Result<EvmAccountsResult, TaskError>>;
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

  const addAccount = async (chain: string, payload: AccountPayload[] | XpubAccountPayload): Promise<Result<string, TaskError>> => {
    const address = Array.isArray(payload) ? payload.map(item => item.address).join(',\n') : payload.xpub.xpub;
    const subject = { chain, target: accountTargetOf(payload) };
    const outcome = await submitTask<string[] | true>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      lane: accountAddActivity.laneOf?.(subject),
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<string[] | true, TaskError>> => mapResult(
        await runTask<string[] | true>(
          async () => addBlockchainAccount(chain, payload),
        ),
        value => value,
      ),
      subtitle: accountActivityLabel.add(address),
      title: t('task_center.group.accounts'),
    });

    // `''` used to mean three different things at once: cancelled, non-actionable failure, and a
    // genuinely empty result. The caller read all three as a successful addition, so a cancelled
    // add was reported as added. Cancellation and failure are now the error branch, and an empty
    // result joins them: nothing was added, so there is no address to hand back, and returning
    // `ok('')` would put `{ address: '' }` into `addedAccounts` and refresh on a blank address.
    return flatMapResult(outcome, (result) => {
      if (result === true)
        return ok(address);

      return result.length > 0
        ? ok(result[0])
        : err(TaskFailed({ message: `no account was added for ${address}` }));
    });
  };

  const addEvmAccount = async ({ address, label, tags }: AccountPayload): Promise<Result<EvmAccountsResult, TaskError>> => {
    // The pseudo-chain, not a real one: this asks for every EVM chain at once.
    const subject: AccountSubject = { chain: EVM_PSEUDO_CHAIN, target: { address, kind: 'address' } };
    const outcome = await submitTask<EvmAccountsResult>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      lane: accountAddActivity.laneOf?.(subject),
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<EvmAccountsResult, TaskError>> => mapResult(
        await runTask<EvmAccountsResult>(
          async () => addEvmAccountCaller({ address, label, tags }),
        ),
        value => value,
      ),
      subtitle: accountActivityLabel.add(address),
      title: t('task_center.group.accounts'),
    });

    // As in `addAccount`: `{}` conflated a cancelled/failed add with an empty result.
    return outcome;
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
    const subject: AccountSubject = { chain, target: { addresses: accounts, kind: 'addresses' } };
    const outcome = await submitTask({
      id: accountRemoveActivity.id(subject),
      kind: accountRemoveActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BlockchainBalances>(
          async () => removeBlockchainAccount(chain, accounts),
        ),
        () => {},
      ),
      subtitle: accountActivityLabel.removeCount(accounts.length),
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
      subtitle: accountActivityLabel.remove(address),
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
    const subject: AccountSubject = {
      chain: params.chain,
      target: { derivationPath: params.derivationPath, kind: 'xpub', xpub: params.xpub },
    };
    const outcome = await submitTask({
      id: accountRemoveActivity.id(subject),
      kind: accountRemoveActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => deleteXpubCaller(params),
        ),
        () => {},
      ),
      subtitle: accountActivityLabel.removeXpub(params.xpub),
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
