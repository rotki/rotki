import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import AccountingRuleActionDialog from '@/modules/settings/accounting/rule/AccountingRuleActionDialog.vue';
import '@test/i18n';

const AccountingRuleActionButton = defineComponent({
  name: 'AccountingRuleActionButton',
  props: ['icon', 'title', 'subtitle'],
  emits: ['click'],
  template: '<button data-testid="rule-action" @click="$emit(\'click\')">{{ title }}</button>',
});

function mountDialog(props: { hasEventSpecificRule?: boolean; hasGeneralRule?: boolean; loadError?: unknown } = {}): VueWrapper {
  return mount(AccountingRuleActionDialog, {
    global: {
      provide: libraryDefaults,
      stubs: {
        AccountingRuleActionButton,
        AccountingRuleEventsDialog: true,
        AccountingRuleViewEventsButton: true,
        RuiDialog: { template: '<div><slot /></div>' },
      },
    },
    props: { hasEventSpecificRule: false, hasGeneralRule: false, ...props },
  });
}

describe('accountingRuleActionDialog', () => {
  it('should name a failed read and offer no action, since which rules exist is unknown', () => {
    const wrapper = mountDialog({ loadError: new Error('backend down') });

    expect(wrapper.find('[data-testid=accounting-rule-action-load-error]').text()).toContain('backend down');
    expect(wrapper.findAll('[data-testid=rule-action]')).toHaveLength(0);
  });

  it('should ask to read the rules again from the failure', async () => {
    const wrapper = mountDialog({ loadError: new Error('backend down') });

    await wrapper.find('[data-testid=table-failure-strip-retry]').trigger('click');

    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should offer adding a general rule only when the read found none', () => {
    const wrapper = mountDialog();

    const titles = wrapper.findAll('[data-testid=rule-action]').map(button => button.text());
    expect(titles).toContain('accounting_settings.rule.action_dialog.add_general');
    expect(wrapper.find('[data-testid=accounting-rule-action-load-error]').exists()).toBe(false);
  });
});
