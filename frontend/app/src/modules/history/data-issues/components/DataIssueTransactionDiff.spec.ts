import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { mount } from '@vue/test-utils';
import { assert, describe, expect, it } from 'vitest';
import DataIssueTransactionDiff from '@/modules/history/data-issues/components/DataIssueTransactionDiff.vue';

describe('dataIssueTransactionDiff', () => {
  it('should hide unchanged events and expand them on request', async () => {
    const transaction = createDecodingComparison();
    const saved = transaction.savedEvents[0];
    assert(saved);
    const unchanged = { ...saved, sequenceIndex: 0, userNotes: 'Unchanged gas fee' };
    const wrapper = mount(DataIssueTransactionDiff, {
      global: { stubs: { DataIssueComparisonEvent: { props: ['diff'], template: '<li>{{ diff.status }}</li>' }, DateDisplay: true, HistoryEventAccount: true, RuiButton: { template: '<button><slot /></button>' } } },
      props: { asset: 'ETH', transaction: { ...transaction, savedEvents: [unchanged, saved], decodedEvents: [unchanged] } },
    });
    expect(wrapper.get('[data-testid="data-issue-review-diffs"]').text()).toBe('removed');
    expect(wrapper.get('[data-testid="data-issue-diff-toggle-unchanged"]').text()).toBe('data_issues.detail.comparison.show_unchanged::1');
    await wrapper.get('[data-testid="data-issue-diff-toggle-unchanged"]').trigger('click');
    expect(wrapper.get('[data-testid="data-issue-review-diffs"]').text()).toContain('unchanged');
    expect(wrapper.findAllComponents({ name: 'HistoryEventAccount' })).toHaveLength(1);
    expect(wrapper.findAllComponents({ name: 'DateDisplay' })).toHaveLength(1);
    await wrapper.get('[data-testid="data-issue-diff-toggle-unchanged"]').trigger('click');
    expect(wrapper.get('[data-testid="data-issue-review-diffs"]').text()).toBe('removed');
  });
});
