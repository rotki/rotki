import type { Ref } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';
import { type UnmatchedBridgeTransaction, useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useUntrackedBridgeCounterpart } from '@/modules/history/events/use-untracked-bridge-counterpart';

interface UseBridgeTransactionActionsOptions {
  /** Invoked after an ignore/restore/external action succeeds, e.g. to clear highlights. */
  onActionComplete?: () => Promise<void>;
}

interface UseBridgeTransactionActionsReturn {
  ignoreLoading: Readonly<Ref<boolean>>;
  modelSelectedIgnored: Ref<string[]>;
  modelSelectedUnmatched: Ref<string[]>;
  confirmCreateCounterpart: (transaction: UnmatchedBridgeTransaction) => void;
  confirmIgnoreSelected: () => void;
  confirmMarkExternal: (transaction: UnmatchedBridgeTransaction) => void;
  confirmRestoreSelected: () => void;
  ignoreTransaction: (transaction: UnmatchedBridgeTransaction) => Promise<void>;
  restoreTransaction: (transaction: UnmatchedBridgeTransaction) => Promise<void>;
}

export function useBridgeTransactionActions(
  options: UseBridgeTransactionActionsOptions = {},
): UseBridgeTransactionActionsReturn {
  const { onActionComplete } = options;

  const { t } = useI18n({ useScope: 'global' });

  const {
    ignoredTransactions,
    refreshUnmatchedBridgeTransactions,
    resolveCreateCounterpart,
    resolveExternal,
    unmatchedTransactions,
  } = useUnmatchedBridgeTransactions();

  const { matchBridgeTransactions, unlinkBridgeTransaction } = useBridgeMatchingApi();
  const { show } = useConfirmStore();
  const { showErrorMessage } = useNotifications();
  const { getChainName } = useSupportedChains();
  const { isCounterpartUntracked } = useUntrackedBridgeCounterpart();

  const ignoreLoading = shallowRef<boolean>(false);
  const modelSelectedUnmatched = ref<string[]>([]);
  const modelSelectedIgnored = ref<string[]>([]);

  /**
   * A row that just left the list must not stay selected, otherwise the "ignore selected"
   * count keeps counting a leg that is no longer actionable. Rows are keyed by the leg
   * event identifier, since a transaction group can carry several bridge legs.
   */
  function deselect(transaction: UnmatchedBridgeTransaction): void {
    const rowId = transaction.identifier.toString();
    set(modelSelectedUnmatched, get(modelSelectedUnmatched).filter(id => id !== rowId));
    set(modelSelectedIgnored, get(modelSelectedIgnored).filter(id => id !== rowId));
  }

  function notifyActionFailure(logMessage: string, error: unknown): void {
    logger.error(logMessage, error);
    showErrorMessage(
      t('actions.bridge_matching.error.title'),
      t('actions.bridge_matching.error.description', { error: getErrorMessage(error) }),
    );
  }

  function formatChain(chain: string | number | undefined): string | undefined {
    if (chain === undefined)
      return undefined;
    return typeof chain === 'number' ? chain.toString() : getChainName(chain);
  }

  async function ignoreTransaction(transaction: UnmatchedBridgeTransaction): Promise<void> {
    set(ignoreLoading, true);
    try {
      await matchBridgeTransactions(transaction.identifier);
      deselect(transaction);
      await refreshUnmatchedBridgeTransactions();
      await onActionComplete?.();
    }
    catch (error: unknown) {
      notifyActionFailure('Failed to ignore bridge transaction:', error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function restoreTransaction(transaction: UnmatchedBridgeTransaction): Promise<void> {
    set(ignoreLoading, true);
    try {
      await unlinkBridgeTransaction(transaction.identifier);
      deselect(transaction);
      await refreshUnmatchedBridgeTransactions();
      await onActionComplete?.();
    }
    catch (error: unknown) {
      notifyActionFailure('Failed to restore bridge transaction:', error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function markExternal(transaction: UnmatchedBridgeTransaction): Promise<void> {
    set(ignoreLoading, true);
    try {
      const result = await resolveExternal(transaction.identifier);
      if (result.success) {
        deselect(transaction);
        await refreshUnmatchedBridgeTransactions();
        await onActionComplete?.();
      }
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function buildMarkExternalOutMessage(untracked: boolean, chain?: string, address?: string): string {
    if (untracked && address) {
      return chain
        ? t('bridge_matching.actions.mark_external_confirm_untracked_chain', { address, chain })
        : t('bridge_matching.actions.mark_external_confirm_untracked', { address });
    }
    if (chain && address)
      return t('bridge_matching.actions.mark_external_confirm_destination', { address, chain });
    if (address)
      return t('bridge_matching.actions.mark_external_confirm_address', { address });
    if (chain)
      return t('bridge_matching.actions.mark_external_confirm_chain', { chain });
    return t('bridge_matching.actions.mark_external_confirm');
  }

  function buildMarkExternalInMessage(untracked: boolean, chain?: string, address?: string): string {
    if (untracked && address) {
      return chain
        ? t('bridge_matching.actions.mark_external_in_confirm_untracked_chain', { address, chain })
        : t('bridge_matching.actions.mark_external_in_confirm_untracked', { address });
    }
    if (chain && address)
      return t('bridge_matching.actions.mark_external_in_confirm_source', { address, chain });
    if (address)
      return t('bridge_matching.actions.mark_external_in_confirm_address', { address });
    if (chain)
      return t('bridge_matching.actions.mark_external_in_confirm_chain', { chain });
    return t('bridge_matching.actions.mark_external_in_confirm');
  }

  async function createCounterpart(transaction: UnmatchedBridgeTransaction): Promise<void> {
    set(ignoreLoading, true);
    try {
      const result = await resolveCreateCounterpart(transaction.identifier);
      if (result.success) {
        deselect(transaction);
        await refreshUnmatchedBridgeTransactions();
        await onActionComplete?.();
      }
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function buildCreateCounterpartMessage(isDeposit: boolean, chain?: string): string {
    if (isDeposit) {
      return chain
        ? t('bridge_matching.actions.create_counterpart_confirm_out_chain', { chain })
        : t('bridge_matching.actions.create_counterpart_confirm_out');
    }
    return chain
      ? t('bridge_matching.actions.create_counterpart_confirm_in_chain', { chain })
      : t('bridge_matching.actions.create_counterpart_confirm_in');
  }

  function confirmCreateCounterpart(transaction: UnmatchedBridgeTransaction): void {
    const isDeposit = transaction.direction === 'deposit';
    const chain = formatChain(isDeposit ? transaction.bridge?.toChain : transaction.bridge?.fromChain);

    show({
      message: buildCreateCounterpartMessage(isDeposit, chain),
      primaryAction: t('common.actions.confirm'),
      title: t('bridge_matching.actions.create_counterpart'),
    }, async () => createCounterpart(transaction));
  }

  function confirmMarkExternal(transaction: UnmatchedBridgeTransaction): void {
    const isDeposit = transaction.direction === 'deposit';
    const chain = formatChain(isDeposit ? transaction.bridge?.toChain : transaction.bridge?.fromChain);
    const address = isDeposit ? transaction.bridge?.toAddress : transaction.bridge?.fromAddress;
    // A verified-untracked counterpart turns the "are you sure" warning into guidance:
    // the counterpart event cannot exist, so resolving as external is the correct action.
    const untracked = isCounterpartUntracked(transaction);

    show({
      message: isDeposit
        ? buildMarkExternalOutMessage(untracked, chain, address)
        : buildMarkExternalInMessage(untracked, chain, address),
      primaryAction: t('common.actions.confirm'),
      title: isDeposit
        ? t('bridge_matching.actions.mark_external')
        : t('bridge_matching.actions.mark_external_in'),
    }, async () => markExternal(transaction));
  }

  async function ignoreSelectedTransactions(rowIds: string[]): Promise<void> {
    set(ignoreLoading, true);
    try {
      const transactions = get(unmatchedTransactions).filter(tx => rowIds.includes(tx.identifier.toString()));
      for (const transaction of transactions)
        await matchBridgeTransactions(transaction.identifier);

      await refreshUnmatchedBridgeTransactions();
      set(modelSelectedUnmatched, []);
    }
    catch (error: unknown) {
      notifyActionFailure('Failed to ignore the selected bridge transactions:', error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function unignoreSelectedTransactions(rowIds: string[]): Promise<void> {
    set(ignoreLoading, true);
    try {
      const transactions = get(ignoredTransactions).filter(tx => rowIds.includes(tx.identifier.toString()));
      for (const transaction of transactions)
        await unlinkBridgeTransaction(transaction.identifier);

      await refreshUnmatchedBridgeTransactions();
      set(modelSelectedIgnored, []);
    }
    catch (error: unknown) {
      notifyActionFailure('Failed to restore the selected bridge transactions:', error);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function confirmIgnoreSelected(): void {
    const count = get(modelSelectedUnmatched).length;
    show({
      message: t('bridge_matching.actions.ignore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('bridge_matching.actions.ignore_selected'),
    }, async () => ignoreSelectedTransactions(get(modelSelectedUnmatched)));
  }

  function confirmRestoreSelected(): void {
    const count = get(modelSelectedIgnored).length;
    show({
      message: t('bridge_matching.actions.restore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('bridge_matching.actions.restore_selected'),
    }, async () => unignoreSelectedTransactions(get(modelSelectedIgnored)));
  }

  return {
    confirmCreateCounterpart,
    confirmIgnoreSelected,
    confirmMarkExternal,
    confirmRestoreSelected,
    ignoreLoading: readonly(ignoreLoading),
    ignoreTransaction,
    restoreTransaction,
    modelSelectedIgnored,
    modelSelectedUnmatched,
  };
}
