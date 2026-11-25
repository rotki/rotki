import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import DataIssueRemediationModals from '@/modules/history/data-issues/components/DataIssueRemediationModals.vue';
import PotentialMatchesDialog from '@/modules/history/events/PotentialMatchesDialog.vue';
import UnmatchedMatchingDialog from '@/modules/history/events/UnmatchedMatchingDialog.vue';

describe('dataIssueRemediationModals', () => {
  it('should track PotentialMatchesDialog visibility via subModalOpen and close matchingOpen on pinned', async () => {
    const wrapper = mount(DataIssueRemediationModals, {
      global: {
        stubs: {
          EventAssetPriceUpdateDialog: true,
          HistoryEventFormDialog: true,
          PotentialMatchesDialog: {
            emits: ['matched', 'pinned', 'update:modelValue'],
            props: ['item', 'kind', 'modelValue'],
            template: '<div data-testid="potential-matches-stub" />',
          },
          UnmatchedMatchingDialog: {
            emits: ['find-match', 'update:modelValue'],
            props: ['kind', 'modelValue'],
            template: '<div data-testid="unmatched-matching-stub" />',
          },
        },
      },
      props: {
        eventForm: undefined,
        matchingOpen: true,
        priceUpdate: undefined,
        subModalOpen: false,
      },
    });

    wrapper.findComponent(UnmatchedMatchingDialog).vm.$emit('find-match', { events: [], groupIdentifier: 'g-1' });
    await nextTick();

    expect(wrapper.emitted('update:subModalOpen')?.at(-1)).toStrictEqual([true]);
    expect(wrapper.find('[data-testid="potential-matches-stub"]').exists()).toBe(true);

    wrapper.findComponent(PotentialMatchesDialog).vm.$emit('pinned');
    await nextTick();

    expect(wrapper.emitted('update:matchingOpen')?.at(-1)).toStrictEqual([false]);
    expect(wrapper.emitted('update:subModalOpen')?.at(-1)).toStrictEqual([false]);
  });
});
