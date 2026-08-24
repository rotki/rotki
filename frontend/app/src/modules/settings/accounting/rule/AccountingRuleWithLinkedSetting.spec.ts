import type {
  AccountingRuleLinkedSettingMap,
  AccountingRuleWithLinkedProperty,
} from '@/modules/settings/types/accounting';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, nextTick, ref } from 'vue';
import '@test/i18n';

const options = ref<AccountingRuleLinkedSettingMap[]>([]);

vi.mock('@/modules/settings/accounting/use-accounting-rule-mappings', () => ({
  useAccountingRuleMappings: vi.fn().mockReturnValue({
    accountingRuleLinkedMappingData: (): typeof options => options,
  }),
}));

const AccountingRuleWithLinkedSetting = (
  await import('@/modules/settings/accounting/rule/AccountingRuleWithLinkedSetting.vue')
).default;

describe('accountingRuleWithLinkedSetting', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountingRuleWithLinkedSetting>>;

  afterEach(() => {
    wrapper?.unmount();
    set(options, []);
  });

  function createWrapper(
    modelValue: AccountingRuleWithLinkedProperty,
  ): VueWrapper<InstanceType<typeof AccountingRuleWithLinkedSetting>> {
    return mount(AccountingRuleWithLinkedSetting, {
      global: {
        stubs: {
          ExternalLink: true,
          RuiCheckbox: { emits: ['update:modelValue'], name: 'RuiCheckbox', props: ['modelValue'], template: '<div />' },
          RuiMenuSelect: {
            emits: ['update:modelValue'],
            name: 'RuiMenuSelect',
            props: ['modelValue', 'options'],
            template: '<div />',
          },
          RuiSwitch: { emits: ['update:modelValue'], name: 'RuiSwitch', props: ['modelValue', 'disabled'], template: '<div />' },
          SuccessDisplay: true,
        },
      },
      props: { hint: 'hint', identifier: 'taxable', label: 'label', modelValue },
    });
  }

  /** The stubs below declare their props at runtime, so their instances are typed loosely. */
  function control(name: string): VueWrapper<ComponentPublicInstance<Record<string, unknown>>> {
    return wrapper.findComponent<ComponentPublicInstance<Record<string, unknown>>>({ name });
  }

  function lastModel(): AccountingRuleWithLinkedProperty {
    const last = wrapper.emitted<[AccountingRuleWithLinkedProperty]>('update:modelValue')?.at(-1);
    assert(last);
    return last[0];
  }

  it('should read an absent linked setting as unlinked', () => {
    wrapper = createWrapper({ value: true });

    expect(control('RuiCheckbox').props('modelValue')).toBe(false);
    expect(control('RuiSwitch').props('modelValue')).toBe(true);
  });

  it('should read a present linked setting as linked', () => {
    wrapper = createWrapper({ linkedSetting: 'includeGasCosts', value: false });

    expect(control('RuiCheckbox').props('modelValue')).toBe(true);
    expect(control('RuiMenuSelect').props('modelValue')).toBe('includeGasCosts');
  });

  it('should disable the value switch while the rule is linked', () => {
    wrapper = createWrapper({ linkedSetting: 'includeGasCosts', value: false });

    // The linked setting decides the value, so editing it by hand would be a lie.
    expect(control('RuiSwitch').props('disabled')).toBe(true);
  });

  it('should carry an edited value into the model', async () => {
    wrapper = createWrapper({ value: false });

    control('RuiSwitch').vm.$emit('update:modelValue', true);
    await nextTick();

    expect(lastModel().value).toBe(true);
  });

  it('should adopt the first option when the link is ticked', async () => {
    set(options, [{ identifier: 'includeGasCosts', label: 'Gas', state: true }]);
    wrapper = createWrapper({ value: true });

    control('RuiCheckbox').vm.$emit('update:modelValue', true);
    await nextTick();

    // The select below has to open on something, so ticking the box chooses for the user.
    expect(lastModel().linkedSetting).toBe('includeGasCosts');
  });

  it('should drop the linked setting when the link is unticked', async () => {
    set(options, [{ identifier: 'includeGasCosts', label: 'Gas', state: true }]);
    wrapper = createWrapper({ linkedSetting: 'includeGasCosts', value: true });

    control('RuiCheckbox').vm.$emit('update:modelValue', false);
    await nextTick();

    // Absent, not empty: the api reads an absent field as "this rule has no link".
    expect(lastModel().linkedSetting).toBeUndefined();
  });

  // The mapping arrives over the api, so a rule opened before it lands has nothing to link to, and
  // a link naming nothing is not a link. Refused outright rather than taken and undone, which would
  // flash the select open on its way back out.
  it('should refuse the link while there is nothing to link to', async () => {
    wrapper = createWrapper({ value: true });

    control('RuiCheckbox').vm.$emit('update:modelValue', true);
    await nextTick();

    expect(control('RuiCheckbox').props('modelValue')).toBe(false);
    expect(wrapper.findComponent({ name: 'RuiMenuSelect' }).exists()).toBe(false);
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should carry a chosen linked setting into the model', async () => {
    set(options, [
      { identifier: 'includeGasCosts', label: 'Gas', state: true },
      { identifier: 'includeCrypto2crypto', label: 'Crypto', state: false },
    ]);
    wrapper = createWrapper({ linkedSetting: 'includeGasCosts', value: true });

    control('RuiMenuSelect').vm.$emit('update:modelValue', 'includeCrypto2crypto');
    await nextTick();

    expect(lastModel().linkedSetting).toBe('includeCrypto2crypto');
  });

  it('should not report an edit the user never made', async () => {
    set(options, [{ identifier: 'includeGasCosts', label: 'Gas', state: true }]);
    wrapper = createWrapper({ linkedSetting: 'includeGasCosts', value: true });
    await nextTick();

    // The negative control: mapping the payload into three controls is not an edit of it.
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });
});
