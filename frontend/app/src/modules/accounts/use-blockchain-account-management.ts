import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { isEveryEvmChain } from '@/modules/accounts/use-account-addition-batch';
import { type AccountAdditionParams, type AdditionSummary, useAccountAdditionService } from '@/modules/accounts/use-account-addition-service';
import { type FetchAccountsParams, type RefreshAccountsParams, useAccountOperations } from '@/modules/accounts/use-account-operations';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type ActivityId, ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface AddAccountsOption {
  wait: boolean;
  /** Set when this addition is one row of a larger operation, such as a CSV import. */
  parent?: ActivityId;
}

/** Nothing was attempted: the add was refused, or it is running detached and has nothing to report. */
const NOTHING_ADDED: AdditionSummary = { added: [], cancelled: false, failed: [] };

interface UseBlockchainAccountManagementReturn {
  addAccounts: (chain: string, data: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption) => Promise<AdditionSummary>;
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (params?: FetchAccountsParams) => Promise<void>;
  refreshAccounts: (params: RefreshAccountsParams) => Promise<void>;
}

export function useBlockchainAccountManagement(): UseBlockchainAccountManagementReturn {
  const accountAdditionService = useAccountAdditionService();
  const { detectEvmAccounts, fetchAccounts, refreshAccounts } = useAccountOperations();

  const { getChainName } = useSupportedChains();
  const { useWorkStatusPrefix } = useTaskCenter();
  const addRunning = useWorkStatusPrefix(ActivityKind.ACCOUNTS, ActivityPart.ADD);
  const { notifyInfo } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * An xpub is added as a single unit, so it has no per-account payload to filter against the existing
   * accounts and enables no modules.
   */
  const resolveAdditionPayload = (chain: string, payload: AddAccountsPayload | XpubAccountPayload): {
    filteredPayload: ReturnType<typeof accountAdditionService.getNewAccountPayload>;
    isXpub: boolean;
    modules: AddAccountsPayload['modules'];
  } => {
    if ('xpub' in payload)
      return { filteredPayload: [], isXpub: true, modules: [] };

    return {
      filteredPayload: accountAdditionService.getNewAccountPayload(chain, payload.payload),
      isXpub: false,
      modules: payload.modules,
    };
  };

  /**
   * Whether this request should not proceed, having said why.
   *
   * The running guard is against a user submitting the form twice, not against a batch proceeding.
   * A row of a batch declares its parent, and from the second row onwards an addition is always
   * already running — refusing those silently dropped every row but the first while the progress
   * bar and the completion message still counted them.
   */
  const isRefused = (chain: string, filteredPayload: AccountPayload[], isXpub: boolean, parent?: ActivityId): boolean => {
    if (!parent && get(addRunning).active) {
      logger.debug('account add is already running.');
      return true;
    }

    if (filteredPayload.length > 0 || isXpub)
      return false;

    notifyInfo(
      t('actions.balances.blockchain_accounts_add.task.title', {
        blockchain: isEveryEvmChain(chain) ? chain : getChainName(chain),
      }),
      t('actions.balances.blockchain_accounts_add.no_new.description'),
    );
    return true;
  };

  /**
   * The single addition entry point, whatever the address count.
   *
   * @remarks
   * `chain` may be {@link EVM_PSEUDO_CHAIN} for "every EVM chain", which is a chain value rather
   * than a second function, so one mechanism, error contract and completion shape covers every
   * case.
   *
   * @returns what happened rather than throwing, so the caller decides how to present it: a form
   * can hold its dialog open, a bulk import can tally.
   */
  const addAccounts = async (chain: string, payload: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption): Promise<AdditionSummary> => {
    const { filteredPayload, isXpub, modules } = resolveAdditionPayload(chain, payload);
    if (isRefused(chain, filteredPayload, isXpub, options?.parent))
      return NOTHING_ADDED;

    const onComplete = async (params: AccountAdditionParams): Promise<void> =>
      accountAdditionService.completeAccountAddition(params, refreshAccounts, fetchAccounts);

    const addition = accountAdditionService.addAccounts(
      chain,
      'xpub' in payload ? payload : filteredPayload,
      modules,
      onComplete,
      options?.parent ? { parent: options.parent } : undefined,
    );

    if (!options?.wait) {
      startPromise(addition);
      return NOTHING_ADDED;
    }

    return addition;
  };

  return {
    addAccounts,
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts,
  };
}
