import type { Ref } from 'vue';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { logger } from '@/modules/core/common/logging/logging';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';
import { type UnmatchedBridgeTransaction, useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';

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
  confirmRestoreSelected: () => void;
  markExternal: (transaction: UnmatchedBridgeTransaction) => Promise<void>;
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
  const { notify, showErrorMessage } = useNotifications();
  const { getChainName } = useSupportedChains();

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

  /**
   * Reversible work reports itself with an undo affordance instead of asking first with a
   * modal: both ignoring and resolving as external are undone by the same unlink call,
   * which the backend uses to clear the marker and restore the event from its backup.
   */
  function notifyUndoable(title: string, message: string, transaction: UnmatchedBridgeTransaction): void {
    notify({
      action: {
        action: async () => restoreTransaction(transaction),
        label: t('common.actions.undo'),
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      message,
      priority: Priority.ACTION,
      severity: Severity.INFO,
      title,
    });
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
      notifyUndoable(
        t('actions.bridge_matching.ignored.title'),
        t('actions.bridge_matching.ignored.description'),
        transaction,
      );
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
        notifyUndoable(
          t('actions.bridge_matching.external_success.title'),
          t('actions.bridge_matching.external_success.description'),
          transaction,
        );
      }
    }
    finally {
      set(ignoreLoading, false);
    }
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
    confirmRestoreSelected,
    markExternal,
    ignoreLoading: readonly(ignoreLoading),
    ignoreTransaction,
    restoreTransaction,
    modelSelectedIgnored,
    modelSelectedUnmatched,
  };
}
