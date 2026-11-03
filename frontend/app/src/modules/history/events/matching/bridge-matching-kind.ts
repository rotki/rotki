import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import { msg } from '@/message-key';
import { UnmatchedVariant } from '@/modules/history/events/unmatched-row';
import { useBridgeTransactionActions } from '@/modules/history/events/use-bridge-transaction-actions';
import { type UnmatchedBridgeRow, useUnmatchedBridgeRows } from '@/modules/history/events/use-unmatched-bridge-rows';
import {
  type UnmatchedBridgeTransaction,
  useBridgeEntryLabels,
  useBridgeMatchingFlow,
  useUnmatchedBridgeTransactions,
} from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useBridgeUnmatchableExplanation } from '@/modules/history/events/use-untracked-bridge-counterpart';
import { PinnedNames } from '@/modules/session/types';

/** Cross-chain bridge legs, matched against the leg on the other chain. */
export const bridgeMatchingKind: MatchingKind<UnmatchedBridgeTransaction, UnmatchedBridgeRow> = {
  bulkSelection: { hideWhenEmpty: true, needsTier: false },
  getIdentifier: transaction => transaction.identifier,
  messages: {
    actionFailed: msg.$t('bridge_matching.action_failed'),
    autoMatchTooltip: msg.$t('bridge_matching.actions.auto_match_tooltip'),
    title: msg.$t('bridge_matching.dialog.title'),
  },
  pinnedName: PinnedNames.MATCH_BRIDGE_TRANSACTIONS,
  useActions: (options) => {
    const { ignoreTransaction, restoreTransaction, ...actions } = useBridgeTransactionActions(options);
    return { ...actions, ignore: ignoreTransaction, restore: restoreTransaction };
  },
  useEntryLabels: useBridgeEntryLabels,
  useFlow: useBridgeMatchingFlow,
  useRows: ({ items, ...options }) => useUnmatchedBridgeRows({ ...options, transactions: items }),
  useSource: () => {
    const { ignoredTransactions, refreshUnmatchedBridgeTransactions, triggerBridgeAutoMatching, unmatchedTransactions, ...source } = useUnmatchedBridgeTransactions();
    return {
      ...source,
      autoMatch: triggerBridgeAutoMatching,
      ignored: ignoredTransactions,
      refresh: refreshUnmatchedBridgeTransactions,
      unmatched: unmatchedTransactions,
    };
  },
  useUnmatchableExplanation: subject => useBridgeUnmatchableExplanation(subject).unmatchableExplanation,
  variant: UnmatchedVariant.BRIDGE,
};
