import type { Report } from '@/modules/reports/report-types';
import { createMock } from '@test/utils/create-mock';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { type EffectScope, effectScope, nextTick } from 'vue';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPersistence } from '@/modules/shell/pinned/use-pinned-persistence';

const WIDTH_KEY = 'rotki.pinned.width';
const TABS_KEY = 'rotki.pinned.tabs';

function readTabs(): { names: string[]; activeId: string | null } {
  return JSON.parse(localStorage.getItem(TABS_KEY) ?? '{"activeId":null,"names":[]}');
}

describe('usePinnedPersistence', () => {
  let scope: EffectScope;

  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
  });

  it('should restore the persisted rail width', () => {
    localStorage.setItem(WIDTH_KEY, '720');
    const store = useAreaVisibilityStore();

    scope.run(() => usePinnedPersistence());

    expect(get(store.pinnedWidth)).toBe(720);
  });

  it('should restore persisted tabs without revealing the rail', () => {
    localStorage.setItem(TABS_KEY, JSON.stringify({
      activeId: PinnedNames.INTERNAL_TX_CONFLICTS,
      names: [PinnedNames.MATCH_ASSET_MOVEMENTS, PinnedNames.INTERNAL_TX_CONFLICTS],
    }));
    const store = useAreaVisibilityStore();

    scope.run(() => usePinnedPersistence());

    expect(get(store.pinnedPanels).map(panel => panel.name)).toEqual([
      PinnedNames.MATCH_ASSET_MOVEMENTS,
      PinnedNames.INTERNAL_TX_CONFLICTS,
    ]);
    expect(get(store.activePinnedId)).toBe(PinnedNames.INTERNAL_TX_CONFLICTS);
    // Non-intrusive: the rail stays collapsed until the user opens it.
    expect(get(store.showPinned)).toBe(false);
  });

  it('should skip a non-restorable panel when restoring', () => {
    localStorage.setItem(TABS_KEY, JSON.stringify({
      activeId: PinnedNames.REPORT_ACTIONABLE_CARD,
      names: [PinnedNames.REPORT_ACTIONABLE_CARD, PinnedNames.DATA_ISSUES],
    }));
    const store = useAreaVisibilityStore();

    scope.run(() => usePinnedPersistence());

    // Report needs a live report, so only data-issues is restored and becomes active.
    expect(get(store.pinnedPanels).map(panel => panel.name)).toEqual([PinnedNames.DATA_ISSUES]);
    expect(get(store.activePinnedId)).toBe(PinnedNames.DATA_ISSUES);
  });

  it('should ignore a corrupt or legacy-shaped stored value instead of throwing', () => {
    // `names` is not an array (corruption or an old schema).
    localStorage.setItem(TABS_KEY, JSON.stringify({ activeId: 'x', names: 'oops' }));
    const store = useAreaVisibilityStore();
    const { pinnedPanels } = storeToRefs(store);

    expect(() => scope.run(() => usePinnedPersistence())).not.toThrow();
    expect(get(pinnedPanels)).toHaveLength(0);
  });

  it('should fall back to the default width when the stored width is not a finite number', () => {
    localStorage.setItem(WIDTH_KEY, 'not-a-number');
    const store = useAreaVisibilityStore();
    const { pinnedWidth } = storeToRefs(store);

    scope.run(() => usePinnedPersistence());

    expect(Number.isFinite(get(pinnedWidth))).toBe(true);
  });

  it('should not clobber an already-populated rail', () => {
    localStorage.setItem(TABS_KEY, JSON.stringify({
      activeId: PinnedNames.MATCH_ASSET_MOVEMENTS,
      names: [PinnedNames.MATCH_ASSET_MOVEMENTS],
    }));
    const store = useAreaVisibilityStore();
    store.pinPanel({ name: PinnedNames.DATA_ISSUES, props: {} });

    scope.run(() => usePinnedPersistence());

    expect(get(store.pinnedPanels).map(panel => panel.name)).toEqual([PinnedNames.DATA_ISSUES]);
  });

  it('should persist tabs when a panel is pinned', async () => {
    const store = useAreaVisibilityStore();
    scope.run(() => usePinnedPersistence());

    store.pinPanel({ name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} });
    await nextTick();

    const persisted = readTabs();
    expect(persisted.names).toEqual([PinnedNames.MATCH_ASSET_MOVEMENTS]);
    expect(persisted.activeId).toBe(PinnedNames.MATCH_ASSET_MOVEMENTS);
  });

  it('should not persist a non-restorable panel', async () => {
    const store = useAreaVisibilityStore();
    scope.run(() => usePinnedPersistence());

    store.pinPanel({ name: PinnedNames.DATA_ISSUES, props: {} });
    store.pinPanel({ name: PinnedNames.REPORT_ACTIONABLE_CARD, props: { isPinned: true, report: createMock<Report>() } });
    await nextTick();

    expect(readTabs().names).toEqual([PinnedNames.DATA_ISSUES]);
  });

  it('should persist the width when it changes', async () => {
    const store = useAreaVisibilityStore();
    const { pinnedWidth } = storeToRefs(store);
    scope.run(() => usePinnedPersistence());

    set(pinnedWidth, 640);
    await nextTick();

    expect(localStorage.getItem(WIDTH_KEY)).toBe('640');
  });
});
