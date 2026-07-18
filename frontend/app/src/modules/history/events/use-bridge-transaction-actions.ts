import type { Ref } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useBridgeMatchingApi } from '@/modules/history/api/events/use-bridge-matching-api';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { type UnmatchedBridgeTransaction, useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';

interface UseBridgeTransactionActionsOptions {
  /** Invoked after an ignore/restore/external action succeeds, e.g. to clear highlights. */
  onActionComplete?: () => Promise<void>;
}

interface UseBridgeTransactionActionsReturn {
  ignoreLoading: Ref<boolean>;
  selectedIgnored: Ref<string[]>;
  selectedUnmatched: Ref<string[]>;
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
    resolveExternal,
    unmatchedTransactions,
  } = useUnmatchedBridgeTransactions();

  const { matchBridgeTransactions, unlinkBridgeTransaction } = useBridgeMatchingApi();
  const { show } = useConfirmStore();
  const { getChainName } = useSupportedChains();

  const ignoreLoading = ref<boolean>(false);
  const selectedUnmatched = ref<string[]>([]);
  const selectedIgnored = ref<string[]>([]);

  function getTransactionIdentifier(transaction: UnmatchedBridgeTransaction): number {
    return getEventEntryFromCollection(transaction.events).entry.identifier;
  }

  function formatChain(chain: string | number | undefined): string | undefined {
    if (chain === undefined)
      return undefined;
    return typeof chain === 'number' ? chain.toString() : getChainName(chain);
  }

  async function ignoreTransaction(transaction: UnmatchedBridgeTransaction): Promise<void> {
    set(ignoreLoading, true);
    try {
      await matchBridgeTransactions(getTransactionIdentifier(transaction));
      await refreshUnmatchedBridgeTransactions();
      await onActionComplete?.();
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function restoreTransaction(transaction: UnmatchedBridgeTransaction): Promise<void> {
    set(ignoreLoading, true);
    try {
      await unlinkBridgeTransaction(getTransactionIdentifier(transaction));
      await refreshUnmatchedBridgeTransactions();
      await onActionComplete?.();
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function markExternal(transaction: UnmatchedBridgeTransaction): Promise<void> {
    set(ignoreLoading, true);
    try {
      const result = await resolveExternal(getTransactionIdentifier(transaction));
      if (result.success) {
        await refreshUnmatchedBridgeTransactions();
        await onActionComplete?.();
      }
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function confirmMarkExternal(transaction: UnmatchedBridgeTransaction): void {
    const chain = formatChain(transaction.bridge?.toChain);
    const address = transaction.bridge?.toAddress;

    let message = t('bridge_matching.actions.mark_external_confirm');
    if (chain && address)
      message = t('bridge_matching.actions.mark_external_confirm_destination', { address, chain });
    else if (address)
      message = t('bridge_matching.actions.mark_external_confirm_address', { address });
    else if (chain)
      message = t('bridge_matching.actions.mark_external_confirm_chain', { chain });

    show({
      message,
      primaryAction: t('common.actions.confirm'),
      title: t('bridge_matching.actions.mark_external'),
    }, async () => markExternal(transaction));
  }

  async function ignoreSelectedTransactions(groupIdentifiers: string[]): Promise<void> {
    set(ignoreLoading, true);
    try {
      const transactions = get(unmatchedTransactions).filter(tx => groupIdentifiers.includes(tx.groupIdentifier));
      for (const transaction of transactions)
        await matchBridgeTransactions(getTransactionIdentifier(transaction));

      await refreshUnmatchedBridgeTransactions();
      set(selectedUnmatched, []);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  async function unignoreSelectedTransactions(groupIdentifiers: string[]): Promise<void> {
    set(ignoreLoading, true);
    try {
      const transactions = get(ignoredTransactions).filter(tx => groupIdentifiers.includes(tx.groupIdentifier));
      for (const transaction of transactions)
        await unlinkBridgeTransaction(getTransactionIdentifier(transaction));

      await refreshUnmatchedBridgeTransactions();
      set(selectedIgnored, []);
    }
    finally {
      set(ignoreLoading, false);
    }
  }

  function confirmIgnoreSelected(): void {
    const count = get(selectedUnmatched).length;
    show({
      message: t('bridge_matching.actions.ignore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('bridge_matching.actions.ignore_selected'),
    }, async () => ignoreSelectedTransactions(get(selectedUnmatched)));
  }

  function confirmRestoreSelected(): void {
    const count = get(selectedIgnored).length;
    show({
      message: t('bridge_matching.actions.restore_selected_confirm', { count }),
      primaryAction: t('common.actions.confirm'),
      title: t('bridge_matching.actions.restore_selected'),
    }, async () => unignoreSelectedTransactions(get(selectedIgnored)));
  }

  return {
    confirmIgnoreSelected,
    confirmMarkExternal,
    confirmRestoreSelected,
    ignoreLoading,
    ignoreTransaction,
    restoreTransaction,
    selectedIgnored,
    selectedUnmatched,
  };
}
