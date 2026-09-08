import type { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { shallowMount } from '@vue/test-utils';
import { assert, describe, expect, it, vi } from 'vitest';
import DataIssueComparisonValue from '@/modules/history/data-issues/components/DataIssueComparisonValue.vue';

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): Pick<ReturnType<typeof useHistoryEventMappings>, 'getHistoryEventSubTypeName' | 'getHistoryEventTypeName'> => ({
    getHistoryEventSubTypeName: (type: string): string => type,
    getHistoryEventTypeName: (type: string): string => type,
  }),
}));

describe('dataIssueComparisonValue', () => {
  it('should put saved and decoded values in their respective columns', async () => {
    const transaction = createDecodingComparison();
    const saved = transaction.savedEvents[0];
    const decoded = transaction.decodedEvents[0];
    assert(saved && decoded);
    const wrapper = shallowMount(DataIssueComparisonValue, { props: { field: 'amount', saved, decoded, asset: 'ETH' } });
    expect(wrapper.get('[data-testid="data-issue-diff-before"]').findComponent({ name: 'ValueDisplay' }).props('value').toString()).toBe('2');
    expect(wrapper.get('[data-testid="data-issue-diff-after"]').findComponent({ name: 'ValueDisplay' }).props('value').toString()).toBe('1');
    await wrapper.setProps({ field: 'userNotes' });
    expect(wrapper.get('[data-testid="data-issue-diff-before"]').text()).toContain('My edited spend');
    expect(wrapper.get('[data-testid="data-issue-diff-after"]').text()).toContain('Decoded spend');
  });
});
