import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import AccountingRuleSettingHeader from './AccountingRuleSettingHeader.vue';

describe('accountingRuleSettingHeader', () => {
  function createWrapper(): VueWrapper<InstanceType<typeof AccountingRuleSettingHeader>> {
    return mount(AccountingRuleSettingHeader, {
      global: {
        stubs: {
          RuiMenu: {
            name: 'RuiMenu',
            props: ['modelValue'],
            template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
          },
          SettingCategoryHeader: { template: '<div><slot name="title" /></div>' },
        },
      },
      props: { exportLoading: false, importLoading: false, resetLoading: false },
    });
  }

  it('should ask in the menu before resetting', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=accounting-rule-reset]').trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('accounting_settings.rule.confirm_reset');
    expect(wrapper.emitted('reset')).toBeUndefined();
  });

  it('should reset once accepted', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=accounting-rule-reset]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('reset')).toHaveLength(1);
  });

  it('should not reset when cancelled, and offer the items again next time', async () => {
    const wrapper = createWrapper();
    wrapper.findComponent({ name: 'RuiMenu' }).vm.$emit('update:modelValue', true);
    await nextTick();

    await wrapper.find('[data-testid=accounting-rule-reset]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

    expect(wrapper.emitted('reset')).toBeUndefined();
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=accounting-rule-reset]').exists()).toBe(true);
  });
});
