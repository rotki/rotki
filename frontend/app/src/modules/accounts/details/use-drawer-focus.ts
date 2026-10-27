import type { MaybeRefOrGetter } from 'vue';

/**
 * Moves focus into a drawer when it opens and back to whatever opened it when it closes.
 *
 * @remarks
 * The opener is the element that had focus when the drawer became open, normally the button the
 * user pressed. It is only refocused while it is still in the document, since a closed drawer can
 * outlive the row that opened it.
 *
 * Focus only goes back when it was still in the drawer, or nowhere, as the drawer closed. A drawer
 * closed by a click on the page has already handed focus to what was clicked, such as a search field,
 * and taking it back would leave the user typing into the opener.
 *
 * @param open - whether the drawer currently shows
 * @param focusInside - focuses the first control inside the drawer, run once it has rendered
 * @param within - the drawer's content, to tell focus inside it from focus the user moved elsewhere
 */
export function useDrawerFocus(
  open: MaybeRefOrGetter<boolean>,
  focusInside: () => void,
  within: MaybeRefOrGetter<HTMLElement | null | undefined>,
): void {
  const activeElement = useActiveElement();
  let opener: HTMLElement | undefined;

  watch(() => toValue(open), async (isOpen) => {
    if (isOpen) {
      opener = get(activeElement) ?? undefined;
      await nextTick();
      focusInside();
      return;
    }

    const focused = get(activeElement);
    const movedElsewhere = !!focused && focused !== focused.ownerDocument.body && !toValue(within)?.contains(focused);
    if (!movedElsewhere && opener?.isConnected)
      opener.focus();
    opener = undefined;
  });
}
