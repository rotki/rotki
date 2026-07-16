import type { Nullable } from '@rotki/common';
import type { Pinned, PinnedName } from '@/modules/session/types';
import { logger } from '@/modules/core/common/logging/logging';
import { PINNED_DEFAULT_WIDTH } from '@/modules/shell/layout/sidebar-resize-constants';

/** Maximum number of simultaneously pinned panels. Beyond this the oldest
 * (front of the list) is evicted LRU-style when a new panel is pinned. Also
 * bounds the rail's `<KeepAlive :max>` so cached instances never exceed the cap. */
export const PINNED_CAP = 4;

export const useAreaVisibilityStore = defineStore('session/visibility', () => {
  const showAbout = ref<boolean>(false);
  /** Pinned panels in tab order (front = oldest). Replaces the old single slot. */
  const pinnedPanels = ref<Pinned[]>([]);
  /** The panel currently shown in the rail; null when nothing is pinned. */
  const activePinnedId = ref<Nullable<PinnedName>>(null);
  const showDrawer = ref<boolean>(false);
  const showNotificationBar = ref<boolean>(false);
  const showHelpBar = ref<boolean>(false);
  const showNotesSidebar = ref<boolean>(false);
  const showPinned = ref<boolean>(false);
  const showPrivacyModeMenu = ref<boolean>(false);
  const pinnedWidth = ref<number>(PINNED_DEFAULT_WIDTH);
  const pinnedDragging = ref<boolean>(false);

  /** The active panel as a single entry. Kept for consumers that only care about
   * what is currently shown; the multi-slot state lives in `pinnedPanels`. */
  const pinned = computed<Nullable<Pinned>>(() =>
    get(pinnedPanels).find(panel => panel.name === get(activePinnedId)) ?? null);

  const toggleDrawer = (): void => {
    set(showDrawer, !get(showDrawer));
  };

  /** Pin a panel (or replace an already-pinned one's props in place), focus it,
   * and reveal the rail. Enforces the cap with LRU eviction of the oldest tab. */
  function pinPanel(panel: Pinned): void {
    const panels = [...get(pinnedPanels)];
    const index = panels.findIndex(existing => existing.name === panel.name);
    if (index >= 0) {
      panels[index] = panel;
    }
    else {
      if (panels.length >= PINNED_CAP) {
        // Evict the oldest tab, but never the active one (its content is on screen).
        const activeId = get(activePinnedId);
        const evictIndex = Math.max(0, panels.findIndex(existing => existing.name !== activeId));
        const [evicted] = panels.splice(evictIndex, 1);
        logger.debug(`pinned rail at capacity, evicting ${evicted.name}`);
      }
      panels.push(panel);
    }
    set(pinnedPanels, panels);
    set(activePinnedId, panel.name);
    set(showPinned, true);
  }

  /** Remove a specific panel's tab. If it was active, focus the last remaining
   * tab (or hide the rail when none remain). Other panels are never touched. */
  function unpinPanel(id: PinnedName): void {
    const panels = get(pinnedPanels).filter(panel => panel.name !== id);
    set(pinnedPanels, panels);
    if (get(activePinnedId) === id) {
      const next = panels.at(-1)?.name ?? null;
      set(activePinnedId, next);
      if (!next)
        set(showPinned, false);
    }
  }

  /** Bring an already-pinned panel to the front without changing its props. */
  function focusPanel(id: PinnedName): void {
    if (get(pinnedPanels).some(panel => panel.name === id)) {
      set(activePinnedId, id);
      set(showPinned, true);
    }
  }

  function clearPinned(): void {
    set(pinnedPanels, []);
    set(activePinnedId, null);
    set(showPinned, false);
  }

  const { isXlAndDown } = useBreakpoint();
  const isMini = logicAnd(logicNot(isXlAndDown), logicNot(showDrawer));

  const expanded = logicAnd(logicNot(isXlAndDown), showDrawer);

  return {
    activePinnedId,
    clearPinned,
    expanded,
    focusPanel,
    isMini,
    pinned,
    pinnedDragging,
    pinnedPanels,
    pinnedWidth,
    pinPanel,
    showAbout,
    showDrawer,
    showHelpBar,
    showNotesSidebar,
    showNotificationBar,
    showPinned,
    showPrivacyModeMenu,
    toggleDrawer,
    unpinPanel,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAreaVisibilityStore, import.meta.hot));
