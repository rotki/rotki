import type { MaybeRefOrGetter } from 'vue';

interface UseDrawerDismissOptions {
  /** Whether the drawer is showing; a closed drawer leaves the key alone. */
  open: MaybeRefOrGetter<boolean>;
  /** The drawer's own close, the one its close button uses. */
  close: () => void;
}

interface UseDrawerDismissReturn {
  /** Bind as the `keydown` listener of an element inside the drawer. */
  onKeydown: (event: KeyboardEvent) => void;
}

/**
 * Closes the details drawer with Escape.
 *
 * @remarks
 * Escape is taken on the drawer itself, after anything inside it had its turn: a menu open in the
 * drawer closes on Escape and stops the key there, and dialogs render outside the drawer. A key that
 * arrives while an IME is composing only cancels the composition, so it is left alone.
 *
 * The drawer stays out of the overlay stack. Its close navigates (Back, or a rewrite of the entry),
 * and the stack's Back guard aborts the navigation it intercepts: a layer that navigates from inside
 * that abort sets off the guard again, and the page loops between the two pops.
 */
export function useDrawerDismiss(options: UseDrawerDismissOptions): UseDrawerDismissReturn {
  const { close, open } = options;

  function onKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Escape' || event.defaultPrevented || event.isComposing || !toValue(open))
      return;

    event.preventDefault();
    close();
  }

  return { onKeydown };
}
