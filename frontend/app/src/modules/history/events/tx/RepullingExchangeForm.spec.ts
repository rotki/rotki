import type { StubInstance } from '@test/utils/component-vm';
import type { VueWrapper } from '@vue/test-utils';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import RepullingExchangeForm from '@/modules/history/events/tx/RepullingExchangeForm.vue';
import '@test/i18n';

const KRAKEN: Exchange = { location: 'kraken', name: 'my kraken' };
/** One of the exchanges that reports no date range, so the picker is hidden for it. */
const BITMEX: Exchange = { location: 'bitmex', name: 'my bitmex' };

vi.mock('@/modules/balances/exchanges/use-exchange-data', () => ({
  useExchangeData: (): Record<string, unknown> => ({
    syncingExchanges: computed<Exchange[]>(() => [KRAKEN, BITMEX]),
  }),
}));

function stub(name: string, props: string[]): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'update:start', 'update:end'],
    name,
    props,
    template: '<div />',
  };
}

describe('history/events/tx/RepullingExchangeForm.vue', () => {
  let pinia: Pinia;
  let harness: ModelFormHarness<RepullingTransactionPayload>;

  function basePayload(): RepullingTransactionPayload {
    return {
      address: '',
      chain: 'all',
      fromTimestamp: 1600000000,
      toTimestamp: 1700000000,
    };
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.useFakeTimers();
  });

  afterEach(() => {
    harness?.wrapper.unmount();
    vi.useRealTimers();
  });

  function createWrapper(payload: RepullingTransactionPayload = basePayload()): ModelFormHarness<RepullingTransactionPayload> {
    return mountModelForm(RepullingExchangeForm, {
      errors: {},
      global: {
        plugins: [pinia],
        stubs: {
          DateTimeRangePicker: stub('DateTimeRangePicker', ['start', 'end', 'startErrorMessages', 'endErrorMessages']),
          RuiAlert: stub('RuiAlert', ['type']),
          RuiAutoComplete: stub('RuiAutoComplete', ['modelValue', 'options', 'errorMessages']),
        },
      },
      payload,
    });
  }

  function autocomplete(): VueWrapper<StubInstance> {
    return harness.wrapper.findComponent<StubInstance>({ name: 'RuiAutoComplete' });
  }

  async function chooseExchange(exchange: Exchange = KRAKEN): Promise<void> {
    autocomplete().vm.$emit('update:modelValue', exchange);
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should reject a form with no exchange chosen', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(false);
  });

  it('should accept a form once an exchange is chosen', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await chooseExchange();

    expect(await harness.validate()).toBe(true);
  });

  it.each([
    ['fromTimestamp'],
    ['toTimestamp'],
  ] as const)('should reject a payload with no %s once an exchange is chosen', async (key) => {
    harness = createWrapper({ ...basePayload(), [key]: undefined });
    await vi.advanceTimersToNextTimerAsync();

    await chooseExchange();

    expect(await harness.validate()).toBe(false);
  });

  it('should accept a missing range for an exchange that has no picker', async () => {
    harness = createWrapper({ ...basePayload(), fromTimestamp: undefined, toTimestamp: undefined });
    await vi.advanceTimersToNextTimerAsync();

    await chooseExchange(BITMEX);

    expect(await harness.validate()).toBe(true);
  });

  it('should clear a range carried over when the picker goes away', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await chooseExchange(BITMEX);

    expect(harness.model().fromTimestamp).toBeUndefined();
    expect(harness.model().toTimestamp).toBeUndefined();
  });

  it('should show the form\'s own empty-exchange message, not zod\'s wording, once validate runs', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await harness.validate();
    await vi.advanceTimersToNextTimerAsync();

    const value: unknown = autocomplete().props('errorMessages');
    assert(Array.isArray(value));
    expect(value).toEqual(['transactions.repulling.validation.exchange_non_empty']);
  });

  it('should not arm the close prompt before anything is edited', async () => {
    harness = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(harness.stateUpdated()).toBe(false);
  });

  it('should arm the close prompt once an exchange is chosen', async () => {
    harness = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    await chooseExchange();

    expect(harness.stateUpdated()).toBe(true);
  });

  it('should tell the dialog which exchange was chosen', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await chooseExchange();

    expect(harness.wrapper.findComponent(RepullingExchangeForm).vm.getExchangeData()).toEqual(KRAKEN);
  });

  /*
   * The payload is shared with the blockchain form above this one, where clearing the chain is
   * allowed. This form renders no chain field, so a chain rule here rejects the form with nothing
   * to show for it: the submit button stops working and no message says why.
   */
  it('should accept a form whose shared payload carries no chain', async () => {
    harness = createWrapper({ ...basePayload(), chain: undefined });
    await vi.advanceTimersToNextTimerAsync();

    await chooseExchange();

    expect(await harness.validate()).toBe(true);
  });
});
