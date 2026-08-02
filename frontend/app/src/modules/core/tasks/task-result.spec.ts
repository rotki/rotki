import { err, ok } from 'plainfp/result';
import { assert, describe, expect, it, vi } from 'vitest';
import {
  BackendCancelled,
  Cancelled,
  isActionable,
  isCancellation,
  onActionableError,
  TaskFailed,
} from './task-result';

describe('isCancellation', () => {
  it('should be true for a user cancellation', () => {
    expect(isCancellation(Cancelled({ message: 'boom' }))).toBe(true);
  });

  it('should be true for a backend cancellation', () => {
    expect(isCancellation(BackendCancelled({ message: 'boom' }))).toBe(true);
  });

  it('should be false for an actionable failure', () => {
    expect(isCancellation(TaskFailed({ message: 'boom' }))).toBe(false);
  });
});

describe('isActionable', () => {
  it('should narrow a TaskFailed to the arm carrying the cause', () => {
    const cause = new Error('network');
    const error = TaskFailed({ cause, message: 'boom' });

    assert(isActionable(error));
    expect(error.cause).toBe(cause);
  });

  it('should be false for either cancellation', () => {
    expect(isActionable(Cancelled({ message: 'boom' }))).toBe(false);
    expect(isActionable(BackendCancelled({ message: 'boom' }))).toBe(false);
  });
});

describe('onActionableError', () => {
  it('should run the handler on an actionable failure', () => {
    const handler = vi.fn();
    const error = TaskFailed({ message: 'boom' });

    onActionableError(err(error), handler);

    expect(handler).toHaveBeenCalledWith(error);
  });

  it('should stay silent on a cancellation', () => {
    const handler = vi.fn();

    onActionableError(err(Cancelled({ message: 'boom' })), handler);

    expect(handler).not.toHaveBeenCalled();
  });

  it('should stay silent on success', () => {
    const handler = vi.fn();

    onActionableError(ok(42), handler);

    expect(handler).not.toHaveBeenCalled();
  });
});
