import type { VueWrapper } from '@vue/test-utils';
import type { ComponentPublicInstance } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import { Blockchain } from '@rotki/common';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import RepullingBlockchainForm from '@/modules/history/events/tx/RepullingBlockchainForm.vue';
import '@test/i18n';

const ADDRESS = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12';

const chains = ref<string[]>(['all', Blockchain.ETH]);

vi.mock('@/modules/history/events/tx/use-repulling-transaction-form', () => ({
  shouldShowDateRangePicker: (): boolean => true,
  useRepullingTransactionForm: (): Record<string, unknown> => ({
    chainOptions: computed<string[]>(() => get(chains)),
    getUsableChains: (chain: string | undefined): string[] =>
      !chain || chain === 'all' ? get(chains).filter(item => item !== 'all') : [chain],
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

type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function addressAccount(chain: string, address: string): BlockchainAccount {
  return {
    chain,
    data: { address, type: 'address' },
    nativeAsset: 'ETH',
  };
}

describe('history/events/tx/RepullingBlockchainForm.vue', () => {
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
    set(chains, ['all', Blockchain.ETH]);
    pinia = createPinia();
    setActivePinia(pinia);
    useBlockchainAccountsStore().updateAccounts(Blockchain.ETH, [addressAccount(Blockchain.ETH, ADDRESS)]);
    vi.useFakeTimers();
  });

  afterEach(() => {
    harness?.wrapper.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    payload: RepullingTransactionPayload = basePayload(),
    errors: Record<string, string[] | string> = {},
  ): ModelFormHarness<RepullingTransactionPayload> {
    return mountModelForm(RepullingBlockchainForm, {
      errors,
      global: {
        plugins: [pinia],
        stubs: {
          BlockchainAccountSelector: stub('BlockchainAccountSelector', ['modelValue', 'errorMessages', 'chains']),
          ChainSelect: stub('ChainSelect', ['modelValue', 'errorMessages', 'items']),
          DateTimeRangePicker: stub('DateTimeRangePicker', ['start', 'end', 'startErrorMessages', 'endErrorMessages']),
          RuiAlert: stub('RuiAlert', ['type']),
        },
      },
      payload,
    });
  }

  function field(name: string): VueWrapper<StubInstance> {
    return harness.wrapper.findComponent<StubInstance>({ name });
  }

  function messages(name: string, prop = 'errorMessages'): string[] {
    const value: unknown = field(name).props(prop);
    assert(Array.isArray(value));
    return value.map(String);
  }

  it('should accept a fully filled payload', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(true);
  });

  it.each([
    ['fromTimestamp'],
    ['toTimestamp'],
  ] as const)('should reject a payload with no %s', async (key) => {
    harness = createWrapper({ ...basePayload(), [key]: undefined });
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(false);
  });

  /*
   * The epoch is a date like any other. Vuelidate's `required` reports on a cleared picker, which
   * arrives as undefined, and stringifies 0 to something non-empty - so this passes today, and a
   * port that reaches for a truthiness check would silently start rejecting it.
   */
  it('should accept the epoch as a timestamp', async () => {
    harness = createWrapper({ ...basePayload(), fromTimestamp: 0 });
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(true);
  });

  it('should accept a payload with no chain and no address', async () => {
    harness = createWrapper({ ...basePayload(), address: '', chain: undefined });
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(true);
  });

  // The address carries no rule of its own; it exists only so the api can report against it.
  it('should show a server error reported against the address', async () => {
    harness = createWrapper(basePayload(), { address: ['unknown address'] });
    await vi.advanceTimersToNextTimerAsync();

    await harness.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('BlockchainAccountSelector')).toContain('unknown address');
  });

  it('should show the message for a cleared start date', async () => {
    harness = createWrapper({ ...basePayload(), fromTimestamp: undefined });
    await vi.advanceTimersToNextTimerAsync();

    await harness.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('DateTimeRangePicker', 'startErrorMessages')).not.toEqual([]);
  });

  it('should write a chosen account into the model', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    field('BlockchainAccountSelector').vm.$emit('update:modelValue', [addressAccount(Blockchain.ETH, ADDRESS)]);
    await vi.advanceTimersToNextTimerAsync();

    expect(harness.model().address).toBe(ADDRESS);
  });

  it('should write a chosen chain into the model', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    field('ChainSelect').vm.$emit('update:modelValue', Blockchain.ETH);
    await vi.advanceTimersToNextTimerAsync();

    expect(harness.model().chain).toBe(Blockchain.ETH);
  });

  it('should not arm the close prompt before anything is edited', async () => {
    harness = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(harness.stateUpdated()).toBe(false);
  });

  it('should arm the close prompt once a field is edited', async () => {
    harness = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    field('ChainSelect').vm.$emit('update:modelValue', Blockchain.ETH);
    await vi.advanceTimersToNextTimerAsync();

    expect(harness.stateUpdated()).toBe(true);
  });

  it('should offer nothing to fill in when no chain has an account', async () => {
    set(chains, []);
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(field('ChainSelect').exists()).toBe(false);
    expect(field('RuiAlert').exists()).toBe(true);
  });
});
