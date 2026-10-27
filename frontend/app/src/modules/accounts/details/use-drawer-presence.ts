import type { MaybeRefOrGetter, Ref } from 'vue';

/** How long `RuiNavigationDrawer` takes to slide in or out. */
export const DRAWER_SLIDE_MS = 200;

interface UseDrawerPresenceReturn<T> {
  /** What the drawer shows: the open item, kept while the drawer slides out after it closes. */
  shown: Readonly<Ref<T | undefined>>;
  /** Whether the drawer has finished sliding in, so its heavy content can mount without stalling the slide. */
  ready: Readonly<Ref<boolean>>;
  /** Bind to the drawer's `closed` event, the end of its slide out. */
  onClosed: () => void;
}

/**
 * Keeps a drawer's content in step with its slide.
 *
 * @remarks
 * The item a drawer shows usually goes the moment it closes (here the account leaves the URL), which
 * would empty the drawer at the start of its slide out. `shown` holds on to it until the slide is over.
 *
 * Mounting a long table takes longer than a frame, and done on open it freezes the slide in: the drawer
 * then appears in place instead of moving. `ready` holds the heavy content back until the slide is over.
 * It stays set while the drawer shows another item, and through a reopen before the slide out ended.
 *
 * @param current - the item the drawer is open on, `undefined` while it is closed
 */
export function useDrawerPresence<T>(current: MaybeRefOrGetter<T | undefined>): UseDrawerPresenceReturn<T> {
  const kept = shallowRef<T>();
  const ready = shallowRef<boolean>(false);

  const { start, stop } = useTimeoutFn(() => set(ready, true), DRAWER_SLIDE_MS, { immediate: false });

  function onClosed(): void {
    if (toValue(current) !== undefined)
      return;
    stop();
    set(kept, undefined);
    set(ready, false);
  }

  watchImmediate(() => toValue(current), (item) => {
    if (item === undefined)
      return;
    set(kept, item);
    if (!get(ready))
      start();
  });

  return {
    onClosed,
    ready: readonly(ready),
    shown: computed<T | undefined>(() => get(kept)),
  };
}
