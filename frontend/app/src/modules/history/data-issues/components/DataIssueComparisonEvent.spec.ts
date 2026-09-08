import type { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { shallowMount } from '@vue/test-utils';
import { assert, describe, expect, it, vi } from 'vitest';
import DataIssueComparisonEvent from '@/modules/history/data-issues/components/DataIssueComparisonEvent.vue';
import { diffDecodingEvents } from '@/modules/history/data-issues/decoding-comparison';

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): Pick<ReturnType<typeof useHistoryEventMappings>, 'getHistoryEventSubTypeName' | 'getHistoryEventTypeName'> => ({
    getHistoryEventSubTypeName: (type: string): string => type,
    getHistoryEventTypeName: (type: string): string => type,
  }),
}));

describe('dataIssueComparisonEvent', () => {
  it('should show only differing fields for a modified event', () => {
    const diff = diffDecodingEvents(createDecodingComparison())[0];
    assert(diff);
    const wrapper = shallowMount(DataIssueComparisonEvent, { props: { asset: 'ETH', diff } });
    expect(wrapper.get('[data-testid="data-issue-diff-status"]').text()).toBe('data_issues.detail.comparison.modified');
    const fields = wrapper.findAllComponents({ name: 'DataIssueComparisonValue' });
    expect(fields.map(field => field.props('field'))).toEqual(['amount', 'balanceEffect', 'userNotes']);
    expect(fields[0]?.props('saved')).toEqual(diff.saved);
    expect(fields[0]?.props('decoded')).toEqual(diff.decoded);
  });

  it('should show a removed event once without repeating shared account and date', () => {
    const transaction = createDecodingComparison();
    const diff = diffDecodingEvents({ ...transaction, decodedEvents: [] })[0];
    assert(diff?.saved);
    const wrapper = shallowMount(DataIssueComparisonEvent, {
      props: { asset: 'ETH', diff, sharedAccount: diff.saved.locationLabel ?? undefined, sharedTimestamp: diff.saved.timestamp },
    });
    expect(wrapper.get('[data-testid="data-issue-diff-status"]').text()).toBe('data_issues.detail.comparison.removed');
    expect(wrapper.get('[data-testid="data-issue-diff-notes"]').text()).toBe('My edited spend');
    expect(wrapper.findComponent({ name: 'HistoryEventAccount' }).exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'DateDisplay' }).exists()).toBe(false);
    expect(wrapper.findAllComponents({ name: 'DataIssueComparisonValue' })).toHaveLength(0);
  });
});
