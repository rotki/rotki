import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AccountingRuleConflictsBanner from '@/modules/settings/accounting/rule/AccountingRuleConflictsBanner.vue';
import { createRuiPlugin } from '@/plugins/rui';
import '@test/i18n';

const DialogStub = { name: 'AccountingRuleConflictsDialog', template: '<div data-testid="conflicts-dialog" />' };

function createWrapper(props: { count: number; open: boolean }): VueWrapper {
  return mount(AccountingRuleConflictsBanner, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { AccountingRuleConflictsDialog: DialogStub },
    },
    props,
  });
}

describe('accountingRuleConflictsBanner', () => {
  it('should offer the conflicts when there are some', () => {
    const wrapper = createWrapper({ count: 3, open: false });

    expect(wrapper.find('[data-testid=accounting-rule-conflicts]').text()).toContain('3');
    expect(wrapper.find('[data-testid=conflicts-dialog]').exists()).toBe(false);
  });

  it('should draw nothing when there are none and nobody asked', () => {
    const wrapper = createWrapper({ count: 0, open: false });

    expect(wrapper.find('[data-testid=accounting-rule-conflicts]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=conflicts-dialog]').exists()).toBe(false);
  });

  it('should open the dialog when asked even though counting the conflicts failed', () => {
    const wrapper = createWrapper({ count: 0, open: true });

    expect(wrapper.find('[data-testid=accounting-rule-conflicts]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=conflicts-dialog]').exists()).toBe(true);
  });
});
