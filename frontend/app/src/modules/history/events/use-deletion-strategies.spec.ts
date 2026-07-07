import type { SwapGroup, TransactionGroup } from './use-event-analysis';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { buildDeletionConfirmationMessage, DELETION_STRATEGY_TYPE } from './use-deletion-strategies';

// `buildDeletionConfirmationMessage` takes `t` as a parameter (it is not a
// composable), so we hand it the same shared mock the global `useI18n` uses.
// mockT returns `key` alone, or `key::<comma-joined arg values>` when given params.
const t = mockT;

function txGroups(count: number): Map<string, TransactionGroup> {
  const map = new Map<string, TransactionGroup>();
  // only the map size is read, so an empty stub per entry is enough.
  for (let i = 0; i < count; i++)
    map.set(`0x${i}`, createMock<TransactionGroup>());
  return map;
}

describe('buildDeletionConfirmationMessage', () => {
  it('should build a single-transaction delete message', () => {
    const result = buildDeletionConfirmationMessage(
      { transactions: txGroups(1), type: DELETION_STRATEGY_TYPE.DELETE_TRANSACTIONS },
      t,
    );
    expect(result.message).toContain('transactions.events.confirmation.delete.complete_transaction_single');
    expect(result.message).toContain('transactions.events.confirmation.delete.complete_transaction_options');
    expect(result.primaryAction).toBe('transactions.events.confirmation.delete.delete_transaction');
    expect(result.secondaryAction).toBe('transactions.events.confirmation.ignore.action_short');
    expect(result.title).toBe('transactions.events.confirmation.delete.complete_transaction_title');
  });

  it('should switch to the plural transaction key with the count', () => {
    const result = buildDeletionConfirmationMessage(
      { transactions: txGroups(3), type: DELETION_STRATEGY_TYPE.DELETE_TRANSACTIONS },
      t,
    );
    expect(result.message).toContain('complete_transaction_multiple::3');
  });

  it('should build a delete-events message with the event count', () => {
    const result = buildDeletionConfirmationMessage(
      { eventIds: [1, 2, 3], type: DELETION_STRATEGY_TYPE.DELETE_EVENTS },
      t,
    );
    expect(result.message).toBe('transactions.events.confirmation.delete.message_multiple::3');
    expect(result.primaryAction).toBe('common.actions.confirm');
    expect(result.secondaryAction).toBeUndefined();
  });

  it('should aggregate totals across partial swap groups', () => {
    const partialSwapGroups: SwapGroup[] = [
      { groupIds: [1, 2, 3], selectedIds: [1] },
      { groupIds: [4, 5], selectedIds: [4, 5] },
    ];
    const result = buildDeletionConfirmationMessage(
      { partialSwapGroups, type: DELETION_STRATEGY_TYPE.DELETE_PARTIAL_SWAP },
      t,
    );
    // mockT joins arg values in insertion order: groupCount, selectedCount, totalCount
    expect(result.message).toBe('transactions.events.confirmation.delete.partial_swap_warning::2, 3, 5');
    expect(result.title).toBe('transactions.events.confirmation.delete.partial_swap_title');
  });

  it('should build an ignore-events message from the transaction size', () => {
    const result = buildDeletionConfirmationMessage(
      { transactions: txGroups(2), type: DELETION_STRATEGY_TYPE.IGNORE_EVENTS },
      t,
    );
    expect(result.message).toBe('transactions.events.confirmation.ignore.message_multiple::2');
    expect(result.primaryAction).toBe('transactions.events.confirmation.ignore.confirm');
  });

  it('should default counts to zero when collections are missing', () => {
    const result = buildDeletionConfirmationMessage(
      { type: DELETION_STRATEGY_TYPE.DELETE_EVENTS },
      t,
    );
    expect(result.message).toContain('message_multiple::0');
  });

  it('should throw on an unknown strategy type', () => {
    expect(() => buildDeletionConfirmationMessage(
      { type: 'nonsense' as never },
      t,
    )).toThrow('Unknown deletion strategy');
  });
});
