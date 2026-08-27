import type { StubInstance } from '@test/utils/component-vm';
import type { CustomAsset } from '@/modules/assets/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { settleMountedWork } from '@test/utils/model-form-harness';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import CustomAssetForm from '@/modules/assets/admin/custom/CustomAssetForm.vue';
import '@test/i18n';

const saveIcon = vi.fn<(identifier: string) => void>();

/** Every field is a third-party input, so they are stubbed down to what the form reads back. */
function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'items', 'disabled'],
    template: '<div />',
  };
}

const AssetIconFormStub = {
  methods: { saveIcon },
  name: 'AssetIconForm',
  props: ['identifier'],
  template: '<div />',
};

describe('customAssetForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof CustomAssetForm>>;

  const baseModel = (): CustomAsset => ({
    customAssetType: 'real estate',
    identifier: 'custom-1',
    name: 'A house',
    notes: 'bought in 2019',
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    saveIcon.mockClear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    modelValue: CustomAsset = baseModel(),
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof CustomAssetForm>> {
    return mount(CustomAssetForm, {
      global: {
        stubs: {
          AssetIconForm: AssetIconFormStub,
          AutoCompleteWithSearchSync: inputStub('AutoCompleteWithSearchSync'),
          RuiTextArea: inputStub('RuiTextArea'),
          RuiTextField: inputStub('RuiTextField'),
        },
      },
      props: { errorMessages: {}, modelValue, types: ['real estate', 'art'], ...props },
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(testId: string, value: string | undefined): Promise<void> {
    const input = field(testId);
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  function lastModel(): CustomAsset {
    const updates = wrapper.emitted<[CustomAsset]>('update:modelValue');
    assert(updates);
    return updates.at(-1)![0];
  }

  it('should pass validation when the name and the type are filled', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it.each([
    ['name'],
    ['customAssetType'],
  ] as const)('should fail validation when %s is empty', async (key) => {
    const model = baseModel();
    model[key] = '';
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should pass validation with no notes at all, since its rule exists only to hold server errors', async () => {
    wrapper = createWrapper({ ...baseModel(), notes: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should treat a whitespace-only name as empty', async () => {
    wrapper = createWrapper({ ...baseModel(), name: '   ' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ ...baseModel(), customAssetType: '', name: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('name')).toEqual([]);
    expect(messages('type')).toEqual([]);
  });

  it('should reveal both messages once validate runs', async () => {
    wrapper = createWrapper({ ...baseModel(), customAssetType: '', name: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    // The e2e suite pins the rendered text of both of these.
    expect(messages('name')).toEqual(['asset_form.name_non_empty']);
    expect(messages('type')).toEqual(['asset_form.type_non_empty']);
  });

  it('should show the name message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('name', '');

    expect(messages('name')).toEqual(['asset_form.name_non_empty']);
    expect(messages('type')).toEqual([]);
  });

  it('should write an edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('name', 'A boat');

    expect(lastModel().name).toBe('A boat');
    expect(lastModel().customAssetType).toBe('real estate');
  });

  it('should keep the type list the caller passed', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(field('type').props('items')).toEqual(['real estate', 'art']);
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    await settleMountedWork();

    await edit('name', 'A boat');

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });

  it('should hand the saved identifier to the icon form', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    wrapper.vm.saveIcon('custom-2');

    expect(saveIcon).toHaveBeenCalledWith('custom-2');
  });

  it('should show a server error on an untouched field', async () => {
    const errorMessages: ValidationErrors = { name: ['already taken'] };
    wrapper = createWrapper(baseModel(), { errorMessages });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('name')).toEqual(['already taken']);
  });
});
