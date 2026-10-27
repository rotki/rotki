import type { MaybeRefOrGetter } from 'vue';

/** Marks a control that opens the details drawer: a click on it switches the account instead of closing. */
export const DRAWER_OPENER_ATTRIBUTE = 'data-account-details-opener';

/** The element the app mounts into. Menus, dialogs and the drawer itself are teleported out of it. */
const APP_ROOT_SELECTOR = '#app';

interface UseDrawerOutsideCloseOptions {
  /** The drawer's content; a click inside it never closes the drawer. */
  target: MaybeRefOrGetter<HTMLElement | null | undefined>;
  /** Whether the drawer is showing; a closed drawer ignores clicks. */
  open: MaybeRefOrGetter<boolean>;
  /** The drawer's own close, the one its close button uses. */
  close: () => void;
}

/**
 * Whether a click outside the drawer is one that should close it.
 *
 * @remarks
 * Only a click on the page itself does. A menu or dialog opened from inside the drawer, such as an
 * asset's actions and their confirmation, renders outside the app root, so working in it must not close
 * the drawer under it. A click on another account's open button switches the drawer to that account.
 */
function closesDrawer(target: EventTarget | null): boolean {
  if (!(target instanceof Element))
    return false;
  return !!target.closest(APP_ROOT_SELECTOR) && !target.closest(`[${DRAWER_OPENER_ATTRIBUTE}]`);
}

/** Closes the details drawer on a click on the page outside it. */
export function useDrawerOutsideClose(options: UseDrawerOutsideCloseOptions): void {
  const { close, open, target } = options;

  onClickOutside(() => toValue(target), (event) => {
    if (toValue(open) && closesDrawer(event.target))
      close();
  });
}
