import type { ComputedRef } from 'vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { type PinnedName, type PinnedPanelProps, toPinned } from '@/modules/session/types';

export interface UsePinnedPanelReturn<K extends PinnedName> {
  /** Whether this panel is the one currently shown in the rail. */
  active: ComputedRef<boolean>;
  /** Whether this panel occupies one of the pinned tabs (shown or backgrounded). */
  isPinned: ComputedRef<boolean>;
  /** Pin this panel with a typed payload (or update its props in place), focus it and reveal the rail. */
  pin: (props: PinnedPanelProps[K]) => void;
  /** Remove this panel's tab. Never touches another panel's tab. */
  unpin: () => void;
  /** Bring this panel's tab to the front without changing its props. */
  focus: () => void;
  /** Hide the rail while keeping every pinned panel mounted. */
  collapse: () => void;
  /** Reveal the rail (used to re-focus an already-pinned panel). */
  reveal: () => void;
  /** Close when this panel is shown; bring to front when pinned-but-hidden; pin otherwise. */
  toggle: (props: PinnedPanelProps[K]) => void;
}

/**
 * Lifecycle wrapper around the multi-slot pinned rail in `useAreaVisibilityStore`.
 * The payload passed to `pin`/`toggle` is type-checked against the panel identified
 * by `id`, which is the typed boundary the old `Record<string, any>` props lacked.
 */
export function usePinnedPanel<K extends PinnedName>(id: K): UsePinnedPanelReturn<K> {
  const store = useAreaVisibilityStore();
  const { activePinnedId, pinnedPanels, showPinned } = storeToRefs(store);

  const active = computed<boolean>(() => get(activePinnedId) === id);
  const isPinned = computed<boolean>(() => get(pinnedPanels).some(panel => panel.name === id));

  function pin(props: PinnedPanelProps[K]): void {
    store.pinPanel(toPinned(id, props));
  }

  function unpin(): void {
    store.unpinPanel(id);
  }

  function focus(): void {
    store.focusPanel(id);
  }

  function collapse(): void {
    set(showPinned, false);
  }

  function reveal(): void {
    set(showPinned, true);
  }

  function toggle(props: PinnedPanelProps[K]): void {
    if (get(isPinned)) {
      if (get(active) && get(showPinned))
        unpin();
      else
        focus();
    }
    else {
      pin(props);
    }
  }

  return { active, collapse, focus, isPinned, pin, reveal, toggle, unpin };
}
