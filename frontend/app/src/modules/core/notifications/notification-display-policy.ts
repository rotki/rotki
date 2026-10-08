import { NotificationKind } from '@rotki/common';

/**
 * Whether a notification of this kind interrupts the user with a popup.
 *
 * @remarks
 * The single place the decision lives. A result, an announcement and a reminder are things the
 * user should see now, so they pop; a backend problem and a background failure are recorded for
 * the drawer and never pop. A caller may still suppress its own popup via `display: false`, which
 * is why this answers the default rather than the final value.
 */
export function displaysFor(kind: NotificationKind): boolean {
  switch (kind) {
    case NotificationKind.ANNOUNCEMENT:
    case NotificationKind.REMINDER:
    case NotificationKind.RESULT:
      return true;
    case NotificationKind.BACKEND_PROBLEM:
    case NotificationKind.FAILURE:
      return false;
  }
}
