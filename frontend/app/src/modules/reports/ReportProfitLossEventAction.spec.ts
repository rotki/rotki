import type { ComponentPublicInstance } from 'vue';
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { ProfitLossEvent } from '@/modules/reports/report-types';
import { bigNumberify, Zero } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const addHistoricalPrice = vi.fn<(payload: HistoricalPriceFormPayload) => Promise<boolean>>();
const resetHistoricalPricesData = vi.fn();
const getHistoricPrice = vi.fn();
const setMessage = vi.fn();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockImplementation(() => ({ addHistoricalPrice })),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn().mockImplementation(() => ({ resetHistoricalPricesData })),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockImplementation(() => ({ getHistoricPrice })),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: vi.fn().mockImplementation(() => ({ setMessage })),
}));

const ReportProfitLossEventAction = (await import('@/modules/reports/ReportProfitLossEventAction.vue')).default;

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'loading'],
    template: '<div />',
  };
}

describe('reportProfitLossEventAction', () => {
  let wrapper: VueWrapper<InstanceType<typeof ReportProfitLossEventAction>>;

  const event = (): ProfitLossEvent => ({
    assetIdentifier: 'ETH',
    costBasis: null,
    freeAmount: Zero,
    location: 'blockchain',
    notes: null,
    pnlFree: Zero,
    pnlTaxable: Zero,
    price: Zero,
    taxableAmount: Zero,
    timestamp: 1700000000,
    type: 'sell',
  });

  beforeEach(() => {
    vi.clearAllMocks();
    // A value nothing else in the fixture holds, so a write-back that never happens is visible.
    getHistoricPrice.mockResolvedValue(bigNumberify('1234.5'));
    addHistoricalPrice.mockResolvedValue(true);
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(): VueWrapper<InstanceType<typeof ReportProfitLossEventAction>> {
    return mount(ReportProfitLossEventAction, {
      global: {
        stubs: {
          AmountInput: inputStub('AmountInput'),
          AssetSelect: inputStub('AssetSelect'),
          DateTimePicker: inputStub('DateTimePicker'),
          RuiCard: { name: 'RuiCard', template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' },
          // Rendered eagerly, so the dialog contents are reachable without driving the popper.
          RuiDialog: {
            name: 'RuiDialog',
            props: ['modelValue'],
            template: '<div><slot v-if="modelValue" /></div>',
          },
          RuiMenu: {
            name: 'RuiMenu',
            template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
          },
        },
      },
      props: { currency: 'USD', event: event() },
    });
  }

  function field(): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>('[data-testid=edit-historic-price-value]');
  }

  function messages(): string[] {
    const value: unknown = field().props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function openDialog(): Promise<void> {
    await wrapper.find('[data-testid=edit-historic-price-open]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();
    await nextTick();
  }

  async function edit(value: string): Promise<void> {
    const input = field();
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  async function submit(): Promise<void> {
    await wrapper.find('form').trigger('submit');
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should seed the price field from the fetched historic price', async () => {
    wrapper = createWrapper();

    await openDialog();

    expect(getHistoricPrice).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      timestamp: 1700000000,
      toAsset: 'USD',
    });
    expect(field().props('modelValue')).toBe('1234.5');
  });

  it('should seed zero when no historic price is known', async () => {
    getHistoricPrice.mockResolvedValue(Zero);
    wrapper = createWrapper();

    await openDialog();

    expect(field().props('modelValue')).toBe('0');
  });

  it('should show no message before the field is edited', async () => {
    wrapper = createWrapper();
    await openDialog();

    expect(messages()).toEqual([]);
  });

  it('should show the required message once the price is emptied', async () => {
    wrapper = createWrapper();
    await openDialog();

    await edit('');

    expect(messages()).toEqual(['price_form.price_non_empty']);
  });

  it('should treat a whitespace-only price as empty', async () => {
    wrapper = createWrapper();
    await openDialog();

    await edit('   ');

    expect(messages()).toEqual(['price_form.price_non_empty']);
  });

  it('should clear the message once a price is typed again', async () => {
    wrapper = createWrapper();
    await openDialog();

    await edit('');
    await edit('42');

    expect(messages()).toEqual([]);
  });

  it('should save the price and reset the cached entry', async () => {
    wrapper = createWrapper();
    await openDialog();

    await edit('42');
    await submit();

    const payload: HistoricalPriceFormPayload = {
      fromAsset: 'ETH',
      price: '42',
      sourceType: 'manual',
      timestamp: 1700000000,
      toAsset: 'USD',
    };
    expect(addHistoricalPrice).toHaveBeenCalledWith(payload);
    expect(resetHistoricalPricesData).toHaveBeenCalledWith([payload]);
  });

  it('should not save an empty price', async () => {
    wrapper = createWrapper();
    await openDialog();

    await edit('');
    await submit();

    expect(addHistoricalPrice).not.toHaveBeenCalled();
    expect(messages()).toEqual(['price_form.price_non_empty']);
  });

  it('should report a failed save', async () => {
    addHistoricalPrice.mockRejectedValue(new Error('nope'));
    wrapper = createWrapper();
    await openDialog();

    await edit('42');
    await submit();

    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
  });
});
