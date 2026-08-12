import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { RuiAutoCompleteStub } from '@test/stubs/RuiAutoComplete';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import AccountingRuleForm from '@/modules/settings/accounting/rule/AccountingRuleForm.vue';
import { type AccountingRuleEntry, AccountingTreatment } from '@/modules/settings/types/accounting';

/**
 * The two inputs that own the validated fields are heavy (they query counterparties and the
 * type/subtype mappings), so they are replaced by stubs that expose exactly the contract this form
 * relies on: the models it writes, the `error-messages` it feeds them, and the `disabled` flag.
 */
const HistoryEventTypeFormStub = defineComponent({
  emits: ['update:eventType', 'update:eventSubtype', 'touch'],
  name: 'HistoryEventTypeForm',
  props: {
    counterparty: { default: '', type: String },
    disabled: { default: false, type: Boolean },
    errorMessages: { required: true, type: Object },
    eventSubtype: { default: '', type: String },
    eventType: { default: '', type: String },
  },
  setup: () => (): VNode => h('div', { class: 'history-event-type-form' }),
});

const CounterpartyInputStub = defineComponent({
  emits: ['update:modelValue', 'blur'],
  name: 'CounterpartyInput',
  props: {
    disabled: { default: false, type: Boolean },
    errorMessages: { default: (): string[] => [], type: Array },
    modelValue: { default: '', type: String },
  },
  setup: () => (): VNode => h('div', { class: 'counterparty-input' }),
});

type AccountingRuleFormInstance = InstanceType<typeof AccountingRuleForm>;

function createRule(overrides: Partial<AccountingRuleEntry> = {}): AccountingRuleEntry {
  return {
    accountingTreatment: null,
    countCostBasisPnl: { value: false },
    countEntireAmountSpend: { value: false },
    counterparty: null,
    eventSubtype: 'fee',
    eventType: 'spend',
    identifier: 1,
    taxable: { value: false },
    ...overrides,
  };
}

describe('settings/accounting/rule/AccountingRuleForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<AccountingRuleFormInstance>;

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(props: {
    modelValue: AccountingRuleEntry;
    errorMessages?: ValidationErrors;
    eventIds?: number[];
  }): VueWrapper<AccountingRuleFormInstance> {
    return mount(AccountingRuleForm, {
      global: {
        plugins: [pinia],
        stubs: {
          AccountingRuleWithLinkedSetting: true,
          CounterpartyInput: CounterpartyInputStub,
          ExternalLink: true,
          HistoryEventTypeForm: HistoryEventTypeFormStub,
        },
      },
      props: {
        errorMessages: {},
        ...props,
      },
    });
  }

  function typeForm(): VueWrapper<InstanceType<typeof HistoryEventTypeFormStub>> {
    return wrapper.findComponent(HistoryEventTypeFormStub);
  }

  function counterpartyInput(): VueWrapper<InstanceType<typeof CounterpartyInputStub>> {
    return wrapper.findComponent(CounterpartyInputStub);
  }

  it('should seed the inputs from the model', () => {
    wrapper = createWrapper({
      modelValue: createRule({ counterparty: 'uniswap', eventSubtype: 'fee', eventType: 'spend' }),
    });

    expect(typeForm().props('eventType')).toBe('spend');
    expect(typeForm().props('eventSubtype')).toBe('fee');
    expect(counterpartyInput().props('modelValue')).toBe('uniswap');
  });

  it('should show a null counterparty as an empty string', () => {
    wrapper = createWrapper({ modelValue: createRule({ counterparty: null }) });

    expect(counterpartyInput().props('modelValue')).toBe('');
  });

  it('should validate a complete rule', async () => {
    wrapper = createWrapper({ modelValue: createRule() });

    expect(wrapper.vm.validate()).toBe(true);
  });

  it('should reject a rule with no event type', async () => {
    wrapper = createWrapper({ modelValue: createRule({ eventType: '' }) });

    expect(wrapper.vm.validate()).toBe(false);
  });

  it('should reject a rule with no event subtype', async () => {
    wrapper = createWrapper({ modelValue: createRule({ eventSubtype: '' }) });

    expect(wrapper.vm.validate()).toBe(false);
  });

  it('should accept a rule with no counterparty and no accounting treatment', async () => {
    wrapper = createWrapper({
      modelValue: createRule({ accountingTreatment: null, counterparty: null }),
    });

    expect(wrapper.vm.validate()).toBe(true);
  });

  it('should report the required errors on the offending fields once validated', async () => {
    wrapper = createWrapper({ modelValue: createRule({ eventSubtype: '', eventType: '' }) });

    expect(typeForm().props('errorMessages')).toEqual({ eventSubtype: [], eventType: [] });

    wrapper.vm.validate();
    await nextTick();

    const messages = typeForm().props('errorMessages');
    expect(messages.eventType).toHaveLength(1);
    expect(messages.eventSubtype).toHaveLength(1);
  });

  /**
   * Vuelidate read `$externalResults` through `$errors`, which stayed empty until the field was
   * dirty, so a save failure was invisible on a field the user had not touched. The form core shows
   * it straight away, which is what the flow needs: the save that produced the error is the only
   * thing the user just did.
   */
  it('should surface server errors on their fields', async () => {
    wrapper = createWrapper({ modelValue: createRule() });

    await wrapper.setProps({
      errorMessages: {
        counterparty: ['unknown counterparty'],
        eventType: ['not a valid event type'],
      },
    });
    await nextTick();

    expect(typeForm().props('errorMessages').eventType).toStrictEqual(['not a valid event type']);
    expect(counterpartyInput().props('errorMessages')).toStrictEqual(['unknown counterparty']);
  });

  it('should drop a server error once its field is edited', async () => {
    wrapper = createWrapper({ modelValue: createRule() });

    await wrapper.setProps({ errorMessages: { counterparty: ['unknown counterparty'] } });
    expect(counterpartyInput().props('errorMessages')).toStrictEqual(['unknown counterparty']);

    counterpartyInput().vm.$emit('update:modelValue', 'aave');
    await nextTick();

    expect(counterpartyInput().props('errorMessages')).toStrictEqual([]);
  });

  it('should write the counterparty back to the model', async () => {
    const modelValue = createRule({ counterparty: null });
    wrapper = createWrapper({ modelValue });

    counterpartyInput().vm.$emit('update:modelValue', 'aave');
    await nextTick();

    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toMatchObject({ counterparty: 'aave' });
  });

  it('should write the accounting treatment back to the model', async () => {
    wrapper = createWrapper({ modelValue: createRule() });

    wrapper.findComponent(RuiAutoCompleteStub).vm.$emit('update:model-value', AccountingTreatment.SWAP);
    await nextTick();

    expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0])
      .toMatchObject({ accountingTreatment: AccountingTreatment.SWAP });
  });

  it('should offer both accounting treatments, sentence cased', () => {
    wrapper = createWrapper({ modelValue: createRule() });

    expect(wrapper.findComponent(RuiAutoCompleteStub).props('options')).toStrictEqual([
      { identifier: AccountingTreatment.SWAP, label: 'Swap' },
      { identifier: AccountingTreatment.BASIS_TRANSFER, label: 'Basis transfer' },
    ]);
  });

  it('should lock the identifying fields for an event specific rule', () => {
    wrapper = createWrapper({ eventIds: [1, 2], modelValue: createRule() });

    expect(typeForm().props('disabled')).toBe(true);
    expect(counterpartyInput().props('disabled')).toBe(true);
  });

  it('should leave the identifying fields editable without event ids', () => {
    wrapper = createWrapper({ eventIds: [], modelValue: createRule() });

    expect(typeForm().props('disabled')).toBe(false);
    expect(counterpartyInput().props('disabled')).toBe(false);
  });

  it('should leave the state clean while nothing has been edited', async () => {
    wrapper = createWrapper({ modelValue: createRule() });

    await vi.advanceTimersByTimeAsync(1000);

    expect(wrapper.emitted('update:stateUpdated')).toBeUndefined();
  });

  it('should flag the state as updated as soon as a field changes', async () => {
    wrapper = createWrapper({ modelValue: createRule() });

    counterpartyInput().vm.$emit('update:modelValue', 'aave');
    await nextTick();

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toStrictEqual([true]);
  });

  it('should clear the flag when an edit is undone', async () => {
    wrapper = createWrapper({ modelValue: createRule({ counterparty: 'aave' }) });

    counterpartyInput().vm.$emit('update:modelValue', 'uniswap');
    await nextTick();
    counterpartyInput().vm.$emit('update:modelValue', 'aave');
    await nextTick();

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toStrictEqual([false]);
  });

  it('should disarm the dirty flag when it goes away', async () => {
    wrapper = createWrapper({ modelValue: createRule() });

    counterpartyInput().vm.$emit('update:modelValue', 'aave');
    await nextTick();
    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toStrictEqual([true]);

    wrapper.unmount();

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toStrictEqual([false]);
  });
});
