import type { ComputedRef, Ref } from 'vue';
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

/**
 * What the panel says about the resolution the user just made, and the leg an undo would
 * restore. The wording is decided here rather than by the presentation, since it depends on
 * the leg's direction: a resolved deposit is a payment out, a resolved withdrawal is income.
 */
interface BridgeResolutionNotice {
  message: string;
  transaction: UnmatchedBridgeTransaction;
}

interface UseBridgeTransactionActionsReturn {
  ignoreLoading: Readonly<Ref<boolean>>;
  modelSelectedIgnored: Ref<string[]>;
  modelSelectedUnmatched: Ref<string[]>;
  resolutionNotice: ComputedRef<BridgeResolutionNotice | undefined>;
  confirmCreateCounterpart: (transaction: UnmatchedBridgeTransaction) => void;
  confirmIgnoreSelected: () => void;
  confirmRestoreSelected: () => void;
  dismissResolution: () => void;
  markExternal: (transaction: UnmatchedBridgeTransaction) => Promise<void>;
  ignoreTransaction: (transaction: UnmatchedBridgeTransaction) => Promise<void>;
  restoreTransaction: (transaction: UnmatchedBridgeTransaction) => Promise<void>;
  undoResolution: () => Promise<void>;
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

  const ignoreLoading = shallowRef<boolean>(false);
  const modelSelectedUnmatched = ref<string[]>([]);
  const modelSelectedIgnored = ref<string[]>([]);
  const notice = shallowRef<BridgeResolutionNotice>();
  // Exposed through a computed rather than readonly(): the notice carries the leg itself, and
  // deep-readonly does not survive the BigNumber fields its events hold.
  const resolutionNotice = computed<BridgeResolutionNotice | undefined>(() => get(notice));

  /**
   * Drops a row from both selections, so a row that has left the list stops being counted.
   *
   * @remarks
   * Keyed by the leg's event identifier, not the transaction's: one group can carry several legs.
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
   * Reversible work reports with an undo affordance rather than asking first with a modal: both
   * ignoring and resolving as external are undone by the same unlink call.
   *
   * Reported in the panel the action came from, so the outcome and its undo sit beside the list they
   * changed. Holding only the latest resolution costs nothing durable — resolving as external also
   * writes the leg to `history_event_link_ignores`, which keeps a Restore in the ignored tab.
   */
  function reportResolution(message: string, transaction: UnmatchedBridgeTransaction): void {
    set(notice, { message, transaction });
  }

  function dismissResolution(): void {
    set(notice, undefined);
  }

  async function undoResolution(): Promise<void> {
    const current = get(notice);
    if (!current)
      return;

    await restoreTransaction(current.transaction);
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
      reportResolution(t('bridge_matching.resolved.ignored'), transaction);
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
      if (get(notice)?.transaction.identifier === transaction.identifier)
        dismissResolution();

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
        reportResolution(
          transaction.direction === 'deposit'
            ? t('bridge_matching.resolved.external_deposit')
            : t('bridge_matching.resolved.external_withdrawal'),
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
    dismissResolution,
    markExternal,
    ignoreLoading: readonly(ignoreLoading),
    ignoreTransaction,
    restoreTransaction,
    resolutionNotice,
    modelSelectedIgnored,
    modelSelectedUnmatched,
    undoResolution,
  };
}
