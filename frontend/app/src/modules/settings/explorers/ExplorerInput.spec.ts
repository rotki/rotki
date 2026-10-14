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

  /** The save action sits inside the field and only shows once the url differs from the saved one. */
  function saveButton(): DOMWrapper<HTMLButtonElement> {
    const button = wrapper.find<HTMLButtonElement>('[data-testid=explorer-save]');
    assert(button.exists(), 'the save button is missing');
    return button;
  }

  function errorMessage(): string {
    return wrapper.find('.details .text-rui-error').text();
  }

  it('should offer no save while the url is unchanged', () => {
    wrapper = createWrapper('https://example.com/address/');

    expect(wrapper.find('[data-testid=explorer-save]').exists()).toBe(false);
  });

  it('should allow saving an emptied url, which clears the override', async () => {
    wrapper = createWrapper('https://example.com/address/');

    await wrapper.find('input').setValue('');

    expect(saveButton().attributes('disabled')).toBeUndefined();
  });

  it('should save on enter and drop the save action once saved', async () => {
    wrapper = createWrapper();

    await wrapper.find('input').setValue('https://example.com/address/');
    await wrapper.find('input').trigger('keydown', { key: 'Enter' });

    expect(wrapper.emitted('save-data')).toEqual([['https://example.com/address/']]);
    expect(wrapper.find('[data-testid=explorer-save]').exists()).toBe(false);
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

  it('should reject a url that is only a scheme, which fails the url rule alone', async () => {
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
