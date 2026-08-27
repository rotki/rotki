import type { StubInstance } from '@test/utils/component-vm';
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { settleMountedWork } from '@test/utils/model-form-harness';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    useAssetField: vi.fn().mockImplementation(() => computed<string>(() => 'SYM')),
  }),
}));

const HistoricPriceForm = (await import('@/modules/assets/prices/historic/HistoricPriceForm.vue')).default;

/** Every field is a third-party input, so they are stubbed down to the two things the form uses. */
function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

describe('historicPriceForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoricPriceForm>>;

  const baseModel = (): HistoricalPriceFormPayload => ({
    fromAsset: 'ETH',
    price: '2500',
    // Carried through the form untouched: no field renders it and no rule reads it.
    sourceType: 'manual',
    timestamp: 1700000000,
    toAsset: 'USD',
  });

  /** Clearing the date input writes an empty value into the model, which is what its rule guards. */
  function withoutTimestamp(): HistoricalPriceFormPayload {
    const model = baseModel();
    Reflect.deleteProperty(model, 'timestamp');
    return model;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    modelValue: HistoricalPriceFormPayload = baseModel(),
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof HistoricPriceForm>> {
    return mount(HistoricPriceForm, {
      global: {
        stubs: {
          AmountInput: inputStub('AmountInput'),
          AssetSelect: inputStub('AssetSelect'),
          DateTimePicker: inputStub('DateTimePicker'),
        },
      },
      props: { modelValue, ...props },
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

  async function edit(testId: string, value: string | number): Promise<void> {
    const input = field(testId);
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should pass validation when every field is filled', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it.each([
    ['fromAsset'],
    ['toAsset'],
    ['price'],
  ] as const)('should fail validation when %s is empty', async (key) => {
    const model = baseModel();
    model[key] = '';
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should treat a whitespace-only price as empty', async () => {
    wrapper = createWrapper({ ...baseModel(), price: '   ' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should fail validation when the date is cleared', async () => {
    wrapper = createWrapper(withoutTimestamp());
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should accept a zero timestamp, the epoch being a real date rather than a missing one', async () => {
    wrapper = createWrapper({ ...baseModel(), timestamp: 0 });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ ...withoutTimestamp(), fromAsset: '', price: '', toAsset: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('historic-price-from-asset')).toEqual([]);
    expect(messages('historic-price-to-asset')).toEqual([]);
    expect(messages('historic-price-datetime')).toEqual([]);
    expect(messages('historic-price-value')).toEqual([]);
  });

  it('should reveal every message once validate runs', async () => {
    wrapper = createWrapper({ ...withoutTimestamp(), fromAsset: '', price: '', toAsset: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('historic-price-from-asset')).toEqual(['price_form.from_non_empty']);
    expect(messages('historic-price-to-asset')).toEqual(['price_form.to_non_empty']);
    expect(messages('historic-price-datetime')).toEqual(['price_form.date_non_empty']);
    expect(messages('historic-price-value')).toEqual(['price_form.price_non_empty']);
  });

  it('should show the price message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('historic-price-value', '');

    expect(messages('historic-price-value')).toEqual(['price_form.price_non_empty']);
    expect(messages('historic-price-from-asset')).toEqual([]);
  });

  it('should write an edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('historic-price-value', '3000');

    const updates = wrapper.emitted<[HistoricalPriceFormPayload]>('update:modelValue');
    expect(updates).toBeTruthy();
    const last = updates!.at(-1)![0];
    expect(last.price).toBe('3000');
    expect(last.timestamp).toBe(1700000000);
    // The field the form never renders still has to survive the round trip.
    expect(last.sourceType).toBe('manual');
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    await settleMountedWork();

    await edit('historic-price-value', '3000');

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });

  it('should lock everything but the price while editing', async () => {
    wrapper = createWrapper(baseModel(), { editMode: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('historic-price-from-asset').props('disabled')).toBe(true);
    expect(field('historic-price-to-asset').props('disabled')).toBe(true);
    expect(field('historic-price-datetime').props('disabled')).toBe(true);
    expect(field('historic-price-value').props('disabled')).toBeFalsy();
  });

  it('should still gate the locked fields while editing, so a row seeded without one cannot save', async () => {
    wrapper = createWrapper(withoutTimestamp(), { editMode: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });
});
