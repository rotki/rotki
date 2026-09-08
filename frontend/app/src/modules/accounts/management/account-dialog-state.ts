import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { isEqual } from 'es-toolkit';

/**
 * Whether the dialog is adding a validator, which is the only case a premium limit applies to.
 *
 * @remarks
 * Editing an existing validator is always allowed: the limit is on how many are tracked, and an
 * edit does not add one.
 *
 * @param state - what the dialog is showing, absent while it is closed
 * @returns whether a new validator is being added
 */
export function isAddingValidator(state: AccountManageState | undefined): boolean {
  return !!state && state.mode !== 'edit' && state.type === 'validator';
}

/**
 * Whether the account being edited was changed by the user rather than replaced by the dialog
 * opening on something else.
 *
 * @remarks
 * Switching chain means the dialog was pointed at a different account, so its data differing says
 * nothing about the user having edited anything. Opening or closing the dialog is not a change
 * either, which is why an absent side on either end reads as untouched.
 *
 * @param next - the state after the change
 * @param previous - the state before it
 * @returns whether the user edited the account in place
 */
export function hasAccountChanged(
  next: AccountManageState | undefined,
  previous: AccountManageState | undefined,
): boolean {
  if (!next || !previous)
    return false;

  return next.chain === previous.chain && !isEqual(next.data, previous.data);
}
