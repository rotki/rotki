import { get } from '@vueuse/core';
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

  it('should start with zeroed counts', () => {
    const store = useDataIssuesInboxStore();

    expect(get(store.counts)).toStrictEqual(emptyCounts());
    expect(get(store.baselineTotal)).toBe(0);
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

  it('should remove the data-issues tab when dismissing inline panels', () => {
    const store = useDataIssuesInboxStore();
    const visibility = useAreaVisibilityStore();
    const { pinnedPanels } = storeToRefs(visibility);
    visibility.pinPanel({ name: PinnedNames.DATA_ISSUES, props: {} });

    store.dismissInlinePanels();

    expect(get(pinnedPanels)).toHaveLength(0);
  });

  it('should leave an unrelated tab untouched when dismissing inline panels', () => {
    const store = useDataIssuesInboxStore();
    const visibility = useAreaVisibilityStore();
    const { pinnedPanels } = storeToRefs(visibility);
    const other = { name: PinnedNames.MATCH_ASSET_MOVEMENTS, props: {} };
    visibility.pinPanel(other);

    store.dismissInlinePanels();

    expect(get(pinnedPanels)).toStrictEqual([other]);
  });
});
