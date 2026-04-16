import type { SwapGroup, TransactionGroup } from './use-event-analysis';

export const DELETION_STRATEGY_TYPE = {
  DELETE_EVENTS: 'delete-events',
  DELETE_PARTIAL_SWAP: 'delete-partial-swap',
  DELETE_TRANSACTIONS: 'delete-transactions',
  IGNORE_EVENTS: 'ignore-events',
} as const;

type DeletionStrategyType = typeof DELETION_STRATEGY_TYPE[keyof typeof DELETION_STRATEGY_TYPE];

export interface DeletionStrategy {
  eventIds?: number[];
  transactions?: Map<string, TransactionGroup>;
  type: DeletionStrategyType;
  partialSwapGroups?: SwapGroup[];
}

export interface ConfirmationMessage {
  message: string;
  primaryAction: string;
  secondaryAction?: string;
  title: string;
}

export function buildDeletionConfirmationMessage(
  strategy: DeletionStrategy,
  t: (key: string, params?: any) => string,
): ConfirmationMessage {
  switch (strategy.type) {
    case DELETION_STRATEGY_TYPE.DELETE_TRANSACTIONS: {
      const count = strategy.transactions?.size ?? 0;
      const message = count === 1
        ? t('transactions.events.confirmation.delete.complete_transaction_single')
        : t('transactions.events.confirmation.delete.complete_transaction_multiple', { count });
      return {
        message: `${message}\n\n${t('transactions.events.confirmation.delete.complete_transaction_options')}`,
        primaryAction: t('transactions.events.confirmation.delete.delete_transaction'),
        secondaryAction: t('transactions.events.confirmation.ignore.action_short'),
        title: t('transactions.events.confirmation.delete.complete_transaction_title'),
      };
    }

    case DELETION_STRATEGY_TYPE.DELETE_EVENTS:
      return {
        message: t('transactions.events.confirmation.delete.message_multiple', {
          count: strategy.eventIds?.length ?? 0,
        }),
        primaryAction: t('common.actions.confirm'),
        title: t('transactions.events.confirmation.delete.title'),
      };

    case DELETION_STRATEGY_TYPE.DELETE_PARTIAL_SWAP: {
      const totalEvents = strategy.partialSwapGroups?.reduce((sum, group) => sum + group.groupIds.length, 0) ?? 0;
      const selectedEvents = strategy.partialSwapGroups?.reduce((sum, group) => sum + group.selectedIds.length, 0) ?? 0;
      return {
        message: t('transactions.events.confirmation.delete.partial_swap_warning', {
          groupCount: strategy.partialSwapGroups?.length ?? 0,
          selectedCount: selectedEvents,
          totalCount: totalEvents,
        }),
        primaryAction: t('common.actions.confirm'),
        title: t('transactions.events.confirmation.delete.partial_swap_title'),
      };
    }

    case DELETION_STRATEGY_TYPE.IGNORE_EVENTS: {
      const count = strategy.transactions?.size ?? 0;
      return {
        message: t('transactions.events.confirmation.ignore.message_multiple', { count }),
        primaryAction: t('transactions.events.confirmation.ignore.confirm'),
        title: t('transactions.events.confirmation.ignore.title'),
      };
    }

    default:
      throw new Error('Unknown deletion strategy');
  }
}
