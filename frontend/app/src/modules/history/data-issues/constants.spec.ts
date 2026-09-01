import { describe, expect, it } from 'vitest';
import {
  canDismiss,
  canResolveManually,
  canRetry,
  DEFAULT_LIST_STATES,
  IssueKind,
  IssueState,
  NON_TERMINAL_STATES,
} from '@/modules/history/data-issues/constants';

describe('data-issues constants', () => {
  describe('default filter states', () => {
    it('should default the inbox list to open + unresolved (issues needing action)', () => {
      expect(DEFAULT_LIST_STATES).toStrictEqual([IssueState.OPEN, IssueState.UNRESOLVED]);
    });

    it('should exclude the transient auto_remediating state from the default list', () => {
      expect(DEFAULT_LIST_STATES).not.toContain(IssueState.AUTO_REMEDIATING);
    });

    it('should keep auto_remediating in the panel preview (non-terminal) states', () => {
      expect(NON_TERMINAL_STATES).toStrictEqual([
        IssueState.OPEN,
        IssueState.AUTO_REMEDIATING,
        IssueState.UNRESOLVED,
      ]);
    });

    it('should never include terminal states in either default set', () => {
      for (const set of [DEFAULT_LIST_STATES, NON_TERMINAL_STATES]) {
        expect(set).not.toContain(IssueState.RESOLVED);
        expect(set).not.toContain(IssueState.DISMISSED);
      }
    });
  });

  describe('transition guards', () => {
    it.each([
      [IssueState.OPEN, true],
      [IssueState.AUTO_REMEDIATING, true],
      [IssueState.UNRESOLVED, true],
      [IssueState.RESOLVED, false],
      [IssueState.DISMISSED, false],
    ])('canDismiss(%s) === %s', (state, expected) => {
      expect(canDismiss(state)).toBe(expected);
    });

    it.each([
      [IssueState.OPEN, true],
      [IssueState.AUTO_REMEDIATING, true],
      [IssueState.UNRESOLVED, true],
      [IssueState.RESOLVED, false],
      [IssueState.DISMISSED, false],
    ])('canResolveManually(%s) === %s', (state, expected) => {
      expect(canResolveManually(state)).toBe(expected);
    });

    it.each([
      [IssueKind.REBASING_TOKEN, IssueState.OPEN, true],
      [IssueKind.REBASING_TOKEN, IssueState.AUTO_REMEDIATING, false],
      [IssueKind.REBASING_TOKEN, IssueState.UNRESOLVED, true],
      [IssueKind.REBASING_TOKEN, IssueState.RESOLVED, false],
      [IssueKind.REBASING_TOKEN, IssueState.DISMISSED, false],
      [IssueKind.NEGATIVE_BALANCE, IssueState.OPEN, false],
    ])('canRetry(%s, %s) === %s', (kind, state, expected) => {
      expect(canRetry(kind, state)).toBe(expected);
    });
  });
});
