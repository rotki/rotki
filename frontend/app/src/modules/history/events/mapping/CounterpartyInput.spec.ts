import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import '@test/i18n';

const { counterparties } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { counterparties: ref<string[]>(['uniswap-v3', 'aave']) };
});

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => ({
  useHistoryEventCounterpartyMappings: (): object => ({ counterparties }),
}));

/** Records the model and options it is given; tests emit its update to stand in for a pick or a clear. */
const RuiAutoComplete = defineComponent({
  name: 'RuiAutoComplete',
  props: {
    clearable: { default: false, type: Boolean },
    modelValue: { default: undefined, type: String },
    options: { default: () => [], type: Array },
  },
  template: '<div class="rui-auto-complete" />',
});

function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
  return mount(CounterpartyInput, {
    global: {
      stubs: { CounterpartyDisplay: true, RuiAutoComplete },
    },
    props: { modelValue: 'aave', ...props },
  });
}

describe('history/events/mapping/CounterpartyInput', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should always offer the clear button', () => {
    const wrapper = createWrapper();

    expect(wrapper.getComponent(RuiAutoComplete).props('clearable')).toBe(true);
  });

  it('should send the value on clear when the field is cleared, and undefined without one', async () => {
    const withClearValue = createWrapper({ valueOnClear: '' });
    withClearValue.getComponent(RuiAutoComplete).vm.$emit('update:modelValue', undefined);
    await nextTick();
    expect(withClearValue.emitted('update:model-value')).toEqual([['']]);

    const withoutClearValue = createWrapper();
    withoutClearValue.getComponent(RuiAutoComplete).vm.$emit('update:modelValue', undefined);
    await nextTick();
    expect(withoutClearValue.emitted('update:model-value')).toEqual([[undefined]]);
  });

  it('should send a picked counterparty up as is', async () => {
    const wrapper = createWrapper({ valueOnClear: '' });

    wrapper.getComponent(RuiAutoComplete).vm.$emit('update:modelValue', 'uniswap-v3');
    await nextTick();

    expect(wrapper.emitted('update:model-value')).toEqual([['uniswap-v3']]);
  });

  it('should show a clear value that is not a counterparty as no selection', () => {
    const wrapper = createWrapper({ modelValue: null, valueOnClear: null });

    expect(wrapper.getComponent(RuiAutoComplete).props('modelValue')).toBeUndefined();
  });
});
