import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import TwoFieldsAmountInput from '@/modules/shell/components/inputs/TwoFieldsAmountInput.vue';

describe('two-fields-amount-input', () => {
  let wrapper: VueWrapper<InstanceType<typeof TwoFieldsAmountInput>>;

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(): VueWrapper<InstanceType<typeof TwoFieldsAmountInput>> {
    return mount(TwoFieldsAmountInput, {
      global: {
        stubs: {
          AmountInput: {
            methods: { focus: (): void => {} },
            name: 'AmountInput',
            props: ['modelValue', 'label', 'hint'],
            template: '<div><input :value="modelValue" /></div>',
          },
        },
      },
      props: {
        'label': { primary: 'Price', secondary: 'Value' },
        'onUpdate:reversed': async (reversed: boolean) => wrapper.setProps({ reversed }),
        'primaryValue': '2',
        'reversed': false,
        'secondaryValue': '20',
      },
    });
  }

  function toggleButton(text: string): ReturnType<VueWrapper['find']> {
    const button = wrapper.findAll('[data-testid=grouped-amount-input-swap] button').find(item => item.text().includes(text));
    if (!button)
      throw new Error(`no ${text} button`);
    return button;
  }

  it('should switch to entering the value and back', async () => {
    wrapper = createWrapper();

    await toggleButton('common.value').trigger('click');

    expect(wrapper.emitted('update:reversed')?.at(-1)).toEqual([true]);
    expect(wrapper.findComponent({ name: 'AmountInput' }).props('label')).toBe('Value');
    expect(wrapper.findComponent({ name: 'AmountInput' }).props('hint')).toBe('Price: 2');

    await toggleButton('common.price').trigger('click');

    expect(wrapper.emitted('update:reversed')?.at(-1)).toEqual([false]);
    expect(wrapper.findComponent({ name: 'AmountInput' }).props('label')).toBe('Price');
  });
});
