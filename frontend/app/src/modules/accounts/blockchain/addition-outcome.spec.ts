import type { AccountAdditionFailure, AdditionSummary } from '@/modules/accounts/use-account-addition-service';
import { describe, expect, it } from 'vitest';
import { additionError, awaitsAddition, isNothingButCancelled } from '@/modules/accounts/blockchain/addition-outcome';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';

function failure(error: AccountAdditionFailure['error']): AccountAdditionFailure {
  return { account: { address: '0xabc', tags: null }, error };
}

function summary(partial: Partial<AdditionSummary>): AdditionSummary {
  return { added: [], cancelled: false, failed: [], skipped: 0, ...partial };
}

describe('additionError', () => {
  it('should return the cause of a lone failure so a validation error survives', () => {
    const cause = new ApiValidationError('{"address": ["not a valid solana address"]}');

    const error = additionError([failure(TaskFailed({ cause, message: 'wrapped' }))], 'fallback');

    expect(error).toBe(cause);
  });

  it('should use the fallback when a lone failure carries no Error cause', () => {
    expect(additionError([failure(TaskFailed({ message: 'boom' }))], 'fallback'))
      .toStrictEqual(new Error('boom'));
  });

  it('should use the fallback for several failures, since no one field is at fault', () => {
    const cause = new ApiValidationError('{"address": ["bad"]}');
    const failed = [failure(TaskFailed({ cause, message: 'wrapped' })), failure(TaskFailed({ message: 'boom' }))];

    expect(additionError(failed, '2 addresses failed')).toStrictEqual(new Error('2 addresses failed'));
  });
});

describe('isNothingButCancelled', () => {
  it('should be true when every unit was cancelled', () => {
    expect(isNothingButCancelled(summary({ cancelled: true }))).toBe(true);
  });

  it('should be false when something was added', () => {
    expect(isNothingButCancelled(summary({ added: [{ address: '0xabc', chain: 'eth' }], cancelled: true }))).toBe(false);
  });

  it('should be false when something failed for real, even alongside a cancellation', () => {
    expect(isNothingButCancelled(summary({ cancelled: true, failed: [failure(Cancelled({ message: 'x' }))] }))).toBe(false);
  });

  it('should be false when an address was skipped alongside a cancellation, since the dock reports the skip', () => {
    expect(isNothingButCancelled(summary({ cancelled: true, skipped: 1 }))).toBe(false);
  });

  it('should be false for a plain empty summary', () => {
    expect(isNothingButCancelled(summary({}))).toBe(false);
  });
});

describe('awaitsAddition', () => {
  const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

  it('should not wait for well-formed hex addresses on a chain that takes them', () => {
    expect(awaitsAddition([address, address.toLowerCase()], true)).toBe(false);
  });

  it.each([
    ['a mistyped hex address', address.slice(0, -1)],
    ['an ENS name', 'rotki.eth'],
    ['an empty entry', ''],
  ])('should wait for %s', (_, entry) => {
    expect(awaitsAddition([address, entry], true)).toBe(true);
  });

  it('should wait for any address on a chain that takes no hex', () => {
    expect(awaitsAddition([address], false)).toBe(true);
  });
});
