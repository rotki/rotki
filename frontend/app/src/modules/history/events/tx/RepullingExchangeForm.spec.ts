import type { VueWrapper } from '@vue/test-utils';
import type { ComponentPublicInstance } from 'vue';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RepullingExchangeForm from '@/modules/history/events/tx/RepullingExchangeForm.vue';
import '@test/i18n';

const KRAKEN: Exchange = { location: 'kraken', name: 'my kraken' };

vi.mock('@/modules/balances/exchanges/use-exchange-data', () => ({
  useExchangeData: (): Record<string, unknown> => ({
    syncingExchanges: computed<Exchange[]>(() => [KRAKEN]),
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

  async function chooseExchange(): Promise<void> {
    const select: VueWrapper<ComponentPublicInstance> = harness.wrapper.findComponent({ name: 'RuiAutoComplete' });
    select.vm.$emit('update:modelValue', KRAKEN);
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
