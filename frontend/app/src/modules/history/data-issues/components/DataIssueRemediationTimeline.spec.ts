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
