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
  ignoreLoading: Readonly<Ref<boolean>>;
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

  const ignoreLoading = shallowRef<boolean>(false);
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

  function buildMarkExternalOutMessage(chain?: string, address?: string): string {
    if (chain && address)
      return t('bridge_matching.actions.mark_external_confirm_destination', { address, chain });
    if (address)
      return t('bridge_matching.actions.mark_external_confirm_address', { address });
    if (chain)
      return t('bridge_matching.actions.mark_external_confirm_chain', { chain });
    return t('bridge_matching.actions.mark_external_confirm');
  }

  function buildMarkExternalInMessage(chain?: string, address?: string): string {
    if (chain && address)
      return t('bridge_matching.actions.mark_external_in_confirm_source', { address, chain });
    if (address)
      return t('bridge_matching.actions.mark_external_in_confirm_address', { address });
    if (chain)
      return t('bridge_matching.actions.mark_external_in_confirm_chain', { chain });
    return t('bridge_matching.actions.mark_external_in_confirm');
  }

  function confirmMarkExternal(transaction: UnmatchedBridgeTransaction): void {
    const isDeposit = transaction.direction === 'deposit';
    const chain = formatChain(isDeposit ? transaction.bridge?.toChain : transaction.bridge?.fromChain);
    const address = isDeposit ? transaction.bridge?.toAddress : transaction.bridge?.fromAddress;

    show({
      message: isDeposit
        ? buildMarkExternalOutMessage(chain, address)
        : buildMarkExternalInMessage(chain, address),
      primaryAction: t('common.actions.confirm'),
      title: isDeposit
        ? t('bridge_matching.actions.mark_external')
        : t('bridge_matching.actions.mark_external_in'),
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
    ignoreLoading: readonly(ignoreLoading),
    ignoreTransaction,
    restoreTransaction,
    selectedIgnored,
    selectedUnmatched,
  };
}
