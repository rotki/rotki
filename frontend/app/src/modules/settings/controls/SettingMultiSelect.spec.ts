import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SettingMultiSelect from '@/modules/settings/controls/SettingMultiSelect.vue';

const { useSettingModelMock } = vi.hoisted(() => ({ useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const RuiAutoCompleteStub = {
  props: ['modelValue', 'options', 'successMessages'],
  emits: ['update:model-value'],
  template: `<div class="autocomplete">
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
  </div>`,
};

const RuiButtonStub = {
  props: ['disabled'],
  template: `<button class="btn" :disabled="disabled"><slot /></button>`,
};

describe('settingMultiSelect', () => {
  let model: Ref<string[]>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  const options = [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }];

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    return mount(SettingMultiSelect, {
      props: { keyAttr: 'id', options, setting: 'suppressNoIndexerChains', textAttr: 'name', ...props },
      global: { stubs: { RuiAutoComplete: RuiAutoCompleteStub, RuiButton: RuiButtonStub } },
    });
  }

  beforeEach(() => {
    model = ref<string[]>(['a']);
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, model, pending: ref(false), success });
  });

  it('should render the autocomplete with the stored selection', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.autocomplete .model').text()).toContain('a');
  });

  it('should persist a selection change', async () => {
    const wrapper = createWrapper();
    await wrapper.findComponent(RuiAutoCompleteStub).vm.$emit('update:model-value', ['a', 'b']);
    await nextTick();
    expect(get(model)).toStrictEqual(['a', 'b']);
  });

  it('should not render bulk-action buttons by default', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.btn').exists()).toBe(false);
  });

  it('should select all values via the bulk action', async () => {
    const wrapper = createWrapper({ bulkActions: { clearLabel: 'Clear', selectLabel: 'All' } });
    await wrapper.findAll('.btn')[0].trigger('click');
    await nextTick();
    expect(get(model)).toStrictEqual(['a', 'b']);
  });

  it('should clear all values via the bulk action', async () => {
    const wrapper = createWrapper({ bulkActions: { clearLabel: 'Clear', selectLabel: 'All' } });
    await wrapper.findAll('.btn')[1].trigger('click');
    await nextTick();
    expect(get(model)).toStrictEqual([]);
  });

  it('should show a saved success message after a successful write', async () => {
    const wrapper = createWrapper({ successMessage: 'done' });
    set(success, true);
    await nextTick();
    expect(wrapper.find('.success').text()).toContain('done');
  });
});
