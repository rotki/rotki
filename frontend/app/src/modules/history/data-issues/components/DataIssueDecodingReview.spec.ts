import { createDecodingComparison } from '@test/fixtures/decoding-comparison';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import DataIssueDecodingReview from '@/modules/history/data-issues/components/DataIssueDecodingReview.vue';

const push = vi.fn();
vi.mock('vue-router', () => ({ useRouter: (): { push: typeof push } => ({ push }) }));

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
      modelValue: { strategy: 'redecode_customized_transactions', timestamp: 1710000100, transactions: [{ ...transaction, decodedEvents: empty ? [] : transaction.decodedEvents }] },
    },
  });
}

describe('dataIssueDecodingReview', () => {
  it('should open a snapshot with distinct saved and decoded events and explain replacement scope', async () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid="data-issue-review-content"]').exists()).toBe(true);

    const diff = wrapper.findComponent({ name: 'DataIssueTransactionDiff' });
    expect(diff.props('transaction')).toEqual(createDecodingComparison());
    expect(wrapper.text()).toContain('data_issues.detail.comparison.snapshot');
    expect(wrapper.text()).toContain('data_issues.detail.comparison.replacement_warning');
  });

  it('should navigate to the compared transaction and close the review', async () => {
    const wrapper = createWrapper();
    await wrapper.get('[data-testid="data-issue-review-transaction-open"]').trigger('click');

    expect(wrapper.emitted('navigate')).toEqual([['different-transaction']]);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
    expect(push).toHaveBeenCalledWith({ name: '/history/events/', query: { targetGroupIdentifier: 'different-transaction' } });
  });

  it('should pass an empty decoded snapshot to the transaction diff', async () => {
    const wrapper = createWrapper(true);
    expect(wrapper.findComponent({ name: 'DataIssueTransactionDiff' }).props('transaction').decodedEvents).toEqual([]);
  });
});
