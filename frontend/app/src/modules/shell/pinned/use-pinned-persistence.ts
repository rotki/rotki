import type { Nullable } from '@rotki/common';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { type PinnedName, PinnedNames, toPinned } from '@/modules/session/types';
import { PINNED_DEFAULT_WIDTH } from '@/modules/shell/layout/sidebar-resize-constants';
import { PINNED_PANELS } from '@/modules/shell/pinned/pinned-registry';

interface PersistedPinnedTabs {
  /** Pinned panel names in tab order. Props are transient and never persisted. */
  names: PinnedName[];
  /** The panel that was in front, or null. */
  activeId: Nullable<PinnedName>;
}

const WIDTH_KEY = 'rotki.pinned.width';
const TABS_KEY_PREFIX = 'rotki.pinned.tabs';

/**
 * Tabs are stored per user. The rail records what someone was investigating rather than how they
 * like their machine set up, so another user signing in on the same device starts with their own
 * tabs. The width is the opposite - it describes the screen, like the ui language - so it stays
 * device-global.
 */
function tabsKeyFor(username: string): string {
  return `${TABS_KEY_PREFIX}.${username}`;
}

const pinnedNames = new Set<string>(Object.values(PinnedNames));

function isPinnedName(name: string): name is PinnedName {
  return pinnedNames.has(name);
}

/**
 * A panel survives a reload when it can rebuild itself from an empty payload and it still
 * exists in this build. Availability is resolved per call rather than once at import so a
 * flag-gated panel is not baked in at module load.
 */
function isRestorable(name: string): name is PinnedName {
  if (!isPinnedName(name))
    return false;

  const panel = PINNED_PANELS[name];
  return panel.restorable !== false && (panel.available?.() ?? true);
}

/** Falls back to the default when the stored width is corrupt (e.g. `NaN`). */
function validWidth(width: unknown): number {
  return typeof width === 'number' && Number.isFinite(width) ? width : PINNED_DEFAULT_WIDTH;
}

/** Restorable names from a stored value, guarding against a corrupt/legacy shape. */
function restorableNamesFrom(stored: PersistedPinnedTabs | null | undefined): PinnedName[] {
  return (Array.isArray(stored?.names) ? stored.names : []).filter(isRestorable);
}

/** The stored active id if it is still among `names`, else the last tab (or null). */
function resolveActiveId(names: PinnedName[], storedActive: Nullable<PinnedName>): Nullable<PinnedName> {
  return storedActive && names.includes(storedActive) ? storedActive : names.at(-1) ?? null;
}

/**
 * Persists the pinned rail's width and its open tabs (names + active id, never the transient
 * props), and restores them on load. The width is device-local; the tabs are stored per user
 * (see `tabsKeyFor`). Restore is non-intrusive: the tabs come back but the rail stays collapsed
 * until the user opens it (the indicator shows the count). Panels flagged `restorable: false` in
 * the registry (they need live context) are skipped. Call once from the app shell.
 */
export function usePinnedPersistence(): void {
  const store = useAreaVisibilityStore();
  const { activePinnedId, pinnedPanels, pinnedWidth } = storeToRefs(store);
  const { logged, username } = storeToRefs(useSessionAuthStore());

  const persistedWidth = useLocalStorage<number>(WIDTH_KEY, PINNED_DEFAULT_WIDTH);
  // The app shell only mounts once a user is unlocked, and `username` is set before `logged`
  // flips, so the key is bound to the user this rail belongs to.
  const persistedTabs = useLocalStorage<PersistedPinnedTabs>(tabsKeyFor(get(username)), { activeId: null, names: [] });

  // Restore once, and only into an untouched rail so nothing already pinned is clobbered.
  if (get(pinnedPanels).length === 0) {
    set(pinnedWidth, validWidth(get(persistedWidth)));

    const stored = get(persistedTabs);
    const names = restorableNamesFrom(stored);
    if (names.length > 0) {
      set(pinnedPanels, names.map(name => toPinned(name, {})));
      set(activePinnedId, resolveActiveId(names, stored?.activeId ?? null));
    }
  }

  watch(pinnedWidth, (width) => {
    set(persistedWidth, width);
  });

  watch([pinnedPanels, activePinnedId], ([panels, active]) => {
    if (!get(logged))
      return;

    const names = panels.map(panel => panel.name).filter(isRestorable);
    set(persistedTabs, { activeId: resolveActiveId(names, active), names });
  });
}
