import type { RemediationTimelineItem } from '@/modules/history/data-issues/types';
import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { shallowMount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DataIssueRemediationTimeline from '@/modules/history/data-issues/components/DataIssueRemediationTimeline.vue';

describe('dataIssueRemediationTimeline', () => {
  it('should explain when current decoding would change customized transactions', () => {
    const wrapper = shallowMount(DataIssueRemediationTimeline, {
      props: {
        items: [{
          changedTransactionCount: 1,
          customizedTransactionCount: 2,
          result: 'redecoding_would_change_balance',
          strategy: 'redecode_customized_transactions',
        }],
      },
    });

    expect(wrapper.text()).toContain('data_issues.detail.redecoding_would_change_balance');
    expect(wrapper.text()).toContain('data_issues.detail.checked_customizations');
    expect(wrapper.get('[data-testid="data-issue-timeline-counts"]').text()).toBe('data_issues.detail.comparison_counts::2, 1');
    expect(wrapper.find('data-issue-decoding-review-stub').exists()).toBe(false);
    expect(wrapper.text()).toContain('data_issues.detail.comparison_unavailable');
  });

  it('should request stored comparisons even without an affected asset', async () => {
    const item: RemediationTimelineItem = { strategy: 'redecode_customized_transactions', result: 'redecoding_would_change_balance', transactions: [createDecodingComparison()] };
    const wrapper = shallowMount(DataIssueRemediationTimeline, {
      global: { stubs: { RuiButton: { template: '<button><slot /></button>' } } },
      props: { items: [item] },
    });
    await wrapper.get('[data-testid="data-issue-review-open"]').trigger('click');
    expect(wrapper.emitted('review')).toEqual([[item]]);
    expect(wrapper.text()).not.toContain('data_issues.detail.comparison_unavailable');
  });

  it('should explain that a failed comparison left saved events unchanged', () => {
    const wrapper = shallowMount(DataIssueRemediationTimeline, {
      props: {
        items: [{
          result: 'redecoding_failed',
          strategy: 'redecode_customized_transactions',
        }],
      },
    });

    expect(wrapper.text()).toContain('data_issues.detail.redecoding_failed');
  });
});
