import type { Nullable } from '@rotki/common';
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
const TABS_KEY = 'rotki.pinned.tabs';

const restorableNames = new Set<string>(
  Object.values(PinnedNames).filter(name => PINNED_PANELS[name].restorable !== false),
);

function isRestorable(name: string): name is PinnedName {
  return restorableNames.has(name);
}

/**
 * Persists the pinned rail's width and its open tabs (names + active id, never the
 * transient props) to localStorage, and restores them on load. Device-local, like
 * the app's other layout prefs. Restore is non-intrusive: the tabs come back but the
 * rail stays collapsed until the user opens it (the indicator shows the count).
 * Panels flagged `restorable: false` in the registry (they need live context) are
 * skipped. Call once from the app shell.
 */
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

export function usePinnedPersistence(): void {
  const store = useAreaVisibilityStore();
  const { activePinnedId, pinnedPanels, pinnedWidth } = storeToRefs(store);

  const persistedWidth = useLocalStorage<number>(WIDTH_KEY, PINNED_DEFAULT_WIDTH);
  const persistedTabs = useLocalStorage<PersistedPinnedTabs>(TABS_KEY, { activeId: null, names: [] });

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

  // Names + active id change only when the array is replaced by reference (the store
  // never mutates it in place), so a shallow watch is enough and avoids deep-traversing
  // panel props such as the report card's report object.
  watch([pinnedPanels, activePinnedId], ([panels, active]) => {
    const names = panels.map(panel => panel.name).filter(isRestorable);
    set(persistedTabs, { activeId: resolveActiveId(names, active), names });
  });
}
