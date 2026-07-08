import { get, set } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { IssueState } from '@/modules/history/data-issues/constants';
import { emptyCounts, type StateCounts, useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { PinnedNames } from '@/modules/session/types';

function counts(overrides: Partial<StateCounts> = {}): StateCounts {
  return { ...emptyCounts(), ...overrides };
}

describe('useDataIssuesInboxStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should start with zeroed counts and a hidden overlay', () => {
    const store = useDataIssuesInboxStore();

    expect(get(store.counts)).toStrictEqual(emptyCounts());
    expect(get(store.baselineTotal)).toBe(0);
    expect(get(store.overlayVisible)).toBe(false);
    expect(get(store.actionableCount)).toBe(0);
  });

  it('should count only open and unresolved issues as actionable', () => {
    const store = useDataIssuesInboxStore();

    store.setSummary(counts({
      [IssueState.AUTO_REMEDIATING]: 4,
      [IssueState.OPEN]: 3,
      [IssueState.RESOLVED]: 7,
      [IssueState.UNRESOLVED]: 2,
    }), 16);

    // auto-remediating, resolved and dismissed are excluded on purpose.
    expect(get(store.actionableCount)).toBe(5);
  });

  it('should store the counts and baseline handed to setSummary', () => {
    const store = useDataIssuesInboxStore();
    const newCounts = counts({ [IssueState.OPEN]: 1 });

    store.setSummary(newCounts, 42);

    expect(get(store.counts)).toStrictEqual(newCounts);
    expect(get(store.baselineTotal)).toBe(42);
  });

  it('should hide the overlay and clear the data-issues pin when dismissing inline panels', () => {
    const store = useDataIssuesInboxStore();
    const { overlayVisible } = storeToRefs(store);
    const { pinned } = storeToRefs(useAreaVisibilityStore());
    set(overlayVisible, true);
    set(pinned, { name: PinnedNames.DATA_ISSUES, props: {} });

    store.dismissInlinePanels();

    expect(get(overlayVisible)).toBe(false);
    expect(get(pinned)).toBeNull();
  });

  it('should leave an unrelated pin untouched when dismissing inline panels', () => {
    const store = useDataIssuesInboxStore();
    const { pinned } = storeToRefs(useAreaVisibilityStore());
    const other = { name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} };
    set(pinned, other);

    store.dismissInlinePanels();

    expect(get(pinned)).toStrictEqual(other);
  });
});
