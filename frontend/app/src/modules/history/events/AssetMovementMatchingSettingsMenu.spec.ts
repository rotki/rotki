import type { ComponentPublicInstance } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const tolerance = shallowRef<string>('0.05');
const timeRange = shallowRef<number>(7200);

vi.mock('@/modules/settings/use-setting-model', () => ({
  useSettingModel: vi.fn().mockImplementation((key: string) => ({
    error: shallowRef(''),
    model: key === 'assetMovementAmountTolerance' ? tolerance : timeRange,
    pending: shallowRef(false),
    success: shallowRef(false),
  })),
}));

const Menu = (await import('@/modules/history/events/AssetMovementMatchingSettingsMenu.vue')).default;

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

const AmountInputStub = {
  emits: ['update:modelValue'],
  name: 'AmountInput',
  props: ['modelValue', 'errorMessages', 'successMessages', 'label'],
  template: '<div />',
};

describe('assetMovementMatchingSettingsMenu', () => {
  let wrapper: VueWrapper<InstanceType<typeof Menu>>;

  beforeEach(() => {
    setActivePinia(createPinia());
    set(tolerance, '0.05');
    set(timeRange, 7200);
    wrapper = mount(Menu, {
      global: {
        stubs: {
          AmountInput: AmountInputStub,
          RuiMenu: { name: 'RuiMenu', template: '<div><slot name="activator" :attrs="{}" /><slot /></div>' },
        },
      },
      props: { disabled: false },
    });
  });

  /** The tolerance input comes first, the time range second. */
  function input(index: number): VueWrapper<StubInstance> {
    return wrapper.findAllComponents<StubInstance>({ name: 'AmountInput' })[index];
  }

  function messages(index: number): string[] {
    const value: unknown = input(index).props('errorMessages');
    if (!value)
      return [];
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(index: number, value: string): Promise<void> {
    input(index).vm.$emit('update:modelValue', value);
    await nextTick();
  }

  it('should show the stored tolerance as a percentage', () => {
    expect(input(0).props('modelValue')).toBe('5');
  });

  it('should show the stored time range in hours', () => {
    expect(input(1).props('modelValue')).toBe('2');
  });

  it('should write a tolerance back as a fraction', async () => {
    await edit(0, '10');

    expect(get(tolerance)).toBe('0.1');
  });

  it('should write a time range back in seconds', async () => {
    await edit(1, '3');

    expect(get(timeRange)).toBe(10800);
  });

  it.each([
    ['100.1', 'asset_movement_matching.settings.amount_tolerance.validations.max'],
    ['0', 'asset_movement_matching.settings.amount_tolerance.validations.min'],
  ])('should reject a tolerance of %s', async (typed, message) => {
    await edit(0, typed);

    expect(messages(0)).toEqual([message]);
    expect(get(tolerance)).toBe('0.05');
  });

  it('should reject a time range under an hour', async () => {
    await edit(1, '0');

    expect(messages(1)).toEqual(['asset_movement_matching.settings.time_range.validations.min']);
    expect(get(timeRange)).toBe(7200);
  });

  it('should accept the ends of the tolerance range', async () => {
    await edit(0, '100');
    expect(get(tolerance)).toBe('1');

    await edit(0, '0.0001');
    expect(get(tolerance)).toBe('0.000001');
  });

  // Pinned as it stands: `callIfValid` asks the whole validator whether anything is wrong, not the
  // field being written, so one bad field silently stops the other from saving.
  it('should stop a valid time range saving while the tolerance is invalid', async () => {
    await edit(0, '200');

    await edit(1, '5');

    expect(get(timeRange)).toBe(7200);
  });
});
