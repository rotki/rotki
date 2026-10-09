import { NotificationKind } from '@rotki/common';

/**
 * Whether a notification of this kind interrupts the user with a popup.
 *
 * @remarks
 * The single place the decision lives. A result, an announcement and a reminder are things the
 * user should see now, so they pop; a background failure is recorded for the drawer and never
 * pops. A caller may still suppress its own popup via `display: false`, which is why this answers
 * the default rather than the final value.
 */
export function displaysFor(kind: NotificationKind): boolean {
  switch (kind) {
    case NotificationKind.ANNOUNCEMENT:
    case NotificationKind.REMINDER:
    case NotificationKind.RESULT:
      return true;
    case NotificationKind.FAILURE:
      return false;
  }
}
