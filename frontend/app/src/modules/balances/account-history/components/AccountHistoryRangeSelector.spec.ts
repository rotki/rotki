import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { AccountHistoryRange } from '@/modules/balances/account-history/account-history-selection';
import AccountHistoryRangeSelector from '@/modules/balances/account-history/components/AccountHistoryRangeSelector.vue';
import { createRuiPlugin } from '@/plugins/rui';

describe('account history range selector', () => {
  it('should emit the picked range', async () => {
    const wrapper = mount(AccountHistoryRangeSelector, {
      global: { plugins: [createRuiPlugin({})] },
      props: { modelValue: AccountHistoryRange.ALL },
    });

    await wrapper.find(`[data-testid=account-history-range-${AccountHistoryRange.MONTH}]`).trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[AccountHistoryRange.MONTH]]);
  });
});
