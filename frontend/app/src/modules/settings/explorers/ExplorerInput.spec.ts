import { type DOMWrapper, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it } from 'vitest';
import ExplorerInput from '@/modules/settings/explorers/ExplorerInput.vue';

type ExplorerInputInstance = InstanceType<typeof ExplorerInput>;

describe('settings/explorers/ExplorerInput.vue', () => {
  let wrapper: VueWrapper<ExplorerInputInstance>;

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(modelValue: string = ''): VueWrapper<ExplorerInputInstance> {
    return mount(ExplorerInput, {
      props: {
        modelValue,
        'onUpdate:modelValue': async (value: string): Promise<void> => wrapper.setProps({ modelValue: value }),
      },
    });
  }

  /**
   * The save button carries no test id: the e2e page object reaches it as the field's sibling, and it
   * is the last button in the component (the clear button sits inside the text field).
   */
  function saveButton(): DOMWrapper<HTMLButtonElement> {
    const button = wrapper.findAll<HTMLButtonElement>('button').at(-1);
    assert(button, 'the save button is missing');
    return button;
  }

  function errorMessage(): string {
    return wrapper.find('.details .text-rui-error').text();
  }

  it('should allow saving an empty url, which clears the override', () => {
    wrapper = createWrapper();

    expect(saveButton().attributes('disabled')).toBeUndefined();
  });

  it('should allow saving a valid https url', async () => {
    wrapper = createWrapper();

    await wrapper.find('input').setValue('https://example.com/address/');

    expect(wrapper.find('.details .text-rui-error').exists()).toBe(false);
    expect(saveButton().attributes('disabled')).toBeUndefined();
  });

  it('should reject a url that is not https', async () => {
    wrapper = createWrapper();

    await wrapper.find('input').setValue('http://example.com/address/');

    expect(errorMessage()).toBe('explorer_input.validation.https');
    expect(saveButton().attributes('disabled')).toBeDefined();
  });

  // 'https://' passes the https rule and fails only the url rule, so it covers the url check rather
  // than duplicating the test above; an input failing both rules would prove nothing here.
  it('should reject a url that is only a scheme', async () => {
    wrapper = createWrapper();

    await wrapper.find('input').setValue('https://');

    expect(wrapper.find('.details .text-rui-error').exists()).toBe(true);
    expect(saveButton().attributes('disabled')).toBeDefined();
  });

  it('should emit the current url when saving', async () => {
    wrapper = createWrapper();

    await wrapper.find('input').setValue('https://example.com/address/');
    await saveButton().trigger('click');

    expect(wrapper.emitted('save-data')).toEqual([['https://example.com/address/']]);
  });

  it('should empty the field and emit no value when cleared', async () => {
    wrapper = createWrapper('https://example.com/address/');

    await wrapper.find('[data-id=clear-btn]').trigger('click');

    expect(wrapper.props('modelValue')).toBe('');
    expect(wrapper.emitted('save-data')).toEqual([[undefined]]);
  });
});
