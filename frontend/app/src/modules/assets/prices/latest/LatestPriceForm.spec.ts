import type { ComponentPublicInstance } from 'vue';
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    useAssetField: vi.fn().mockImplementation(() => computed<string>(() => 'SYM')),
  }),
}));

const LatestPriceForm = (await import('@/modules/assets/prices/latest/LatestPriceForm.vue')).default;

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

/** Every field is a third-party input, so they are stubbed down to the two things the form uses. */
function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

describe('latestPriceForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof LatestPriceForm>>;

  const baseModel = (): ManualPriceFormPayload => ({
    fromAsset: 'ETH',
    price: '2500',
    toAsset: 'USD',
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    modelValue: ManualPriceFormPayload = baseModel(),
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof LatestPriceForm>> {
    return mount(LatestPriceForm, {
      global: {
        stubs: {
          AmountInput: inputStub('AmountInput'),
          AssetSelect: inputStub('AssetSelect'),
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

  async function edit(testId: string, value: string): Promise<void> {
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

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ fromAsset: '', price: '', toAsset: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('latest-price-from-asset')).toEqual([]);
    expect(messages('latest-price-to-asset')).toEqual([]);
    expect(messages('latest-price-value')).toEqual([]);
  });

  it('should reveal every message once validate runs', async () => {
    wrapper = createWrapper({ fromAsset: '', price: '', toAsset: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('latest-price-from-asset')).toEqual(['price_form.from_non_empty']);
    expect(messages('latest-price-to-asset')).toEqual(['price_form.to_non_empty']);
    expect(messages('latest-price-value')).toEqual(['price_form.price_non_empty']);
  });

  it('should show the price message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('latest-price-value', '');

    expect(messages('latest-price-value')).toEqual(['price_form.price_non_empty']);
    // The untouched fields stay quiet.
    expect(messages('latest-price-from-asset')).toEqual([]);
  });

  it('should write an edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('latest-price-value', '3000');

    const updates = wrapper.emitted<[ManualPriceFormPayload]>('update:modelValue');
    expect(updates).toBeTruthy();
    const last = updates!.at(-1)![0];
    expect(last.price).toBe('3000');
    expect(last.fromAsset).toBe('ETH');
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    // Settle the mounted work first, so what follows is the only edit in play.
    await vi.advanceTimersByTimeAsync(600);

    await edit('latest-price-value', '3000');

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });

  it('should lock the from asset while editing, and leave the price editable', async () => {
    wrapper = createWrapper(baseModel(), { editMode: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('latest-price-from-asset').props('disabled')).toBe(true);
    expect(field('latest-price-to-asset').props('disabled')).toBeFalsy();
    expect(field('latest-price-value').props('disabled')).toBeFalsy();
  });

  it('should lock the from asset when the caller pins it', async () => {
    wrapper = createWrapper(baseModel(), { disableFromAsset: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('latest-price-from-asset').props('disabled')).toBe(true);
  });
});
