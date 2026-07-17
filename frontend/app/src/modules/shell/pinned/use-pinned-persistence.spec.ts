import type { Report } from '@/modules/reports/report-types';
import { createMock } from '@test/utils/create-mock';
import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { type EffectScope, effectScope, nextTick } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPersistence } from '@/modules/shell/pinned/use-pinned-persistence';

const WIDTH_KEY = 'rotki.pinned.width';
const USER = 'alice';
const TABS_KEY = `rotki.pinned.tabs.${USER}`;

function readTabs(key: string = TABS_KEY): { names: string[]; activeId: string | null } {
  return JSON.parse(localStorage.getItem(key) ?? '{"activeId":null,"names":[]}');
}

/** The app shell only mounts for an unlocked user, so every case starts from a signed-in session. */
function signIn(name: string = USER): void {
  const { logged, username } = storeToRefs(useSessionAuthStore());
  set(username, name);
  set(logged, true);
}

describe('usePinnedPersistence', () => {
  let scope: EffectScope;

  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    scope = effectScope();
    signIn();
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

  it('should keep the persisted tabs when logging out empties the rail', async () => {
    const store = useAreaVisibilityStore();
    const { logged } = storeToRefs(useSessionAuthStore());
    scope.run(() => usePinnedPersistence());

    store.pinPanel({ name: PinnedNames.DATA_ISSUES, props: {} });
    await nextTick();
    expect(readTabs().names).toEqual([PinnedNames.DATA_ISSUES]);

    // Logout flips `logged` first, then resets every store, which empties the rail.
    set(logged, false);
    store.clearPinned();
    await nextTick();

    // The rail is empty, but what we restore on the next sign-in must survive.
    expect(get(store.pinnedPanels)).toHaveLength(0);
    expect(readTabs().names).toEqual([PinnedNames.DATA_ISSUES]);
  });

  it('should restore the tabs again on the next sign-in', async () => {
    const first = useAreaVisibilityStore();
    scope.run(() => usePinnedPersistence());
    first.pinPanel({ name: PinnedNames.DATA_ISSUES, props: {} });
    await nextTick();

    // Log out: the stores reset and the app shell unmounts.
    set(storeToRefs(useSessionAuthStore()).logged, false);
    first.clearPinned();
    await nextTick();
    scope.stop();

    // Sign back in: a fresh shell re-runs the composable against an untouched rail.
    setActivePinia(createPinia());
    signIn();
    const second = useAreaVisibilityStore();
    scope = effectScope();
    scope.run(() => usePinnedPersistence());

    expect(get(second.pinnedPanels).map(panel => panel.name)).toEqual([PinnedNames.DATA_ISSUES]);
  });

  it('should not hand one user the tabs of another', async () => {
    const alice = useAreaVisibilityStore();
    scope.run(() => usePinnedPersistence());
    alice.pinPanel({ name: PinnedNames.DATA_ISSUES, props: {} });
    await nextTick();
    scope.stop();

    // Bob signs in on the same device.
    setActivePinia(createPinia());
    signIn('bob');
    const bob = useAreaVisibilityStore();
    scope = effectScope();
    scope.run(() => usePinnedPersistence());

    expect(get(bob.pinnedPanels)).toHaveLength(0);
    // Alice's tabs are untouched, waiting for her next sign-in.
    expect(readTabs().names).toEqual([PinnedNames.DATA_ISSUES]);
  });

  it('should share the rail width across users, since it describes the screen', async () => {
    const { pinnedWidth: aliceWidth } = storeToRefs(useAreaVisibilityStore());
    scope.run(() => usePinnedPersistence());
    set(aliceWidth, 700);
    await nextTick();
    scope.stop();

    setActivePinia(createPinia());
    signIn('bob');
    const { pinnedWidth: bobWidth } = storeToRefs(useAreaVisibilityStore());
    scope = effectScope();
    scope.run(() => usePinnedPersistence());

    expect(get(bobWidth)).toBe(700);
  });
});
