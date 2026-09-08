import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DataIssueDecodingReview from '@/modules/history/data-issues/components/DataIssueDecodingReview.vue';

function createWrapper(empty = false): VueWrapper<InstanceType<typeof DataIssueDecodingReview>> {
  const transaction = createDecodingComparison();
  return mount(DataIssueDecodingReview, {
    global: {
      stubs: {
        DataIssueTransactionDiff: true,
        DateDisplay: true,
        HashLink: true,
        RuiButton: { template: '<button><slot /></button>' },
        RuiCard: { template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' },
        RuiDialog: {
          props: ['modelValue'],
          template: '<div v-if="modelValue"><slot /></div>',
        },
      },
    },
    props: {
      asset: 'ETH',
      timestamp: 1710000100,
      transactions: [{ ...transaction, decodedEvents: empty ? [] : transaction.decodedEvents }],
    },
  });
}

describe('dataIssueDecodingReview', () => {
  it('should open a snapshot with distinct saved and decoded events and explain replacement scope', async () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid="data-issue-review-content"]').exists()).toBe(false);
    await wrapper.get('[data-testid="data-issue-review-open"]').trigger('click');

    const diff = wrapper.findComponent({ name: 'DataIssueTransactionDiff' });
    expect(diff.props('transaction')).toEqual(createDecodingComparison());
    expect(wrapper.text()).toContain('data_issues.detail.comparison.snapshot');
    expect(wrapper.text()).toContain('data_issues.detail.comparison.replacement_warning');
  });

  it('should navigate to the compared transaction and close the review', async () => {
    const wrapper = createWrapper();
    await wrapper.get('[data-testid="data-issue-review-open"]').trigger('click');
    await wrapper.get('[data-testid="data-issue-review-transaction-open"]').trigger('click');

    expect(wrapper.emitted('navigate')).toEqual([['different-transaction']]);
    expect(wrapper.find('[data-testid="data-issue-review-content"]').exists()).toBe(false);
  });

  it('should explain when the decoder would produce no events', async () => {
    const wrapper = createWrapper(true);
    await wrapper.get('[data-testid="data-issue-review-open"]').trigger('click');
    expect(wrapper.findComponent({ name: 'DataIssueTransactionDiff' }).props('transaction').decodedEvents).toEqual([]);
  });
});
