import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

describe('usePinnedPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should report active only for the panel currently shown in the rail', () => {
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    const conflicts = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

    expect(get(match.active)).toBe(false);

    match.pin({});

    expect(get(match.active)).toBe(true);
    expect(get(conflicts.active)).toBe(false);
  });

  it('should pin a typed payload, focus it and reveal the rail', () => {
    const { pinnedPanels, showPinned } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);

    match.pin({ highlightedGroupIdentifier: 'group-1' });

    expect(get(pinnedPanels)).toEqual([
      { name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: { highlightedGroupIdentifier: 'group-1' } },
    ]);
    expect(get(match.active)).toBe(true);
    expect(get(showPinned)).toBe(true);
  });

  it('should keep both panels when a second one is pinned and focus the new one', () => {
    const { pinnedPanels } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    const conflicts = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

    match.pin({});
    conflicts.pin({});

    expect(get(pinnedPanels)).toHaveLength(2);
    expect(get(conflicts.active)).toBe(true);
    expect(get(match.active)).toBe(false);
    // Backgrounded panel is still pinned, just not shown.
    expect(get(match.isPinned)).toBe(true);
  });

  it('should replace props in place when the same panel is pinned again', () => {
    const { pinnedPanels } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);

    match.pin({ highlightedGroupIdentifier: 'group-1' });
    match.pin({ highlightedGroupIdentifier: 'group-2' });

    expect(get(pinnedPanels)).toEqual([
      { name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: { highlightedGroupIdentifier: 'group-2' } },
    ]);
  });

  it('should remove only its own tab on unpin and focus the last remaining', () => {
    const { activePinnedId, pinnedPanels } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    const conflicts = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

    match.pin({});
    conflicts.pin({});

    conflicts.unpin();

    expect(get(pinnedPanels)).toHaveLength(1);
    expect(get(pinnedPanels)[0].name).toBe(PinnedNames.MATCH_ASSET_MOVEMENTS);
    expect(get(activePinnedId)).toBe(PinnedNames.MATCH_ASSET_MOVEMENTS);
  });

  it('should hide the rail when the last tab is unpinned', () => {
    const { showPinned } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);

    match.pin({});
    match.unpin();

    expect(get(showPinned)).toBe(false);
  });

  it('should leave other tabs untouched when unpinning a non-pinned panel', () => {
    const { pinnedPanels } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    const conflicts = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

    match.pin({});
    conflicts.unpin();

    expect(get(pinnedPanels)).toHaveLength(1);
    expect(get(pinnedPanels)[0].name).toBe(PinnedNames.MATCH_ASSET_MOVEMENTS);
  });

  it('should collapse without losing the pinned content', () => {
    const { pinnedPanels, showPinned } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);

    match.pin({});
    match.collapse();

    expect(get(showPinned)).toBe(false);
    expect(get(pinnedPanels)).toHaveLength(1);
  });

  it('should reveal a collapsed rail', () => {
    const { showPinned } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);

    match.pin({});
    match.collapse();
    match.reveal();

    expect(get(showPinned)).toBe(true);
  });

  it('should bring a backgrounded panel to the front on focus', () => {
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    const conflicts = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

    match.pin({});
    conflicts.pin({});
    match.focus();

    expect(get(match.active)).toBe(true);
  });

  it('should pin, focus and close through toggle', () => {
    const { pinnedPanels, showPinned } = storeToRefs(useAreaVisibilityStore());
    const match = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);
    const conflicts = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

    // Not pinned -> pins.
    match.toggle({});
    expect(get(match.active)).toBe(true);

    // Pinned but backgrounded -> focuses instead of closing.
    conflicts.pin({});
    match.toggle({});
    expect(get(match.active)).toBe(true);
    expect(get(pinnedPanels)).toHaveLength(2);

    // Active and shown -> unpins.
    match.toggle({});
    expect(get(match.isPinned)).toBe(false);
    expect(get(showPinned)).toBe(true); // conflicts still pinned
  });

  it('should hold every distinct panel within the cap without eviction', () => {
    const { pinnedPanels } = storeToRefs(useAreaVisibilityStore());
    const names = [
      PinnedNames.DATA_ISSUES,
      PinnedNames.INTERNAL_TX_CONFLICTS,
      PinnedNames.MATCH_ASSET_MOVEMENTS,
      PinnedNames.REPORT_ACTIONABLE_CARD,
    ] as const;

    for (const name of names)
      usePinnedPanel(name).pin({});

    expect(get(pinnedPanels)).toHaveLength(names.length);
    expect(get(pinnedPanels).map(panel => panel.name).sort()).toEqual([...names].sort());
  });
});
