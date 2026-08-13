import type { VueWrapper } from '@vue/test-utils';
import type { ComponentPublicInstance } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { RepullingEthStakingPayload } from '@/modules/history/events/event-payloads';
import { Blockchain, type Eth2ValidatorEntry } from '@rotki/common';
import { type ModelFormHarness, mountModelForm } from '@test/utils/model-form-harness';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import RepullingEthStakingForm from '@/modules/history/events/tx/RepullingEthStakingForm.vue';
import '@test/i18n';

const WITHDRAWAL_ADDRESS = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12';

const VALIDATOR: Eth2ValidatorEntry = {
  index: 42,
  publicKey: '0xaaa',
  status: 'active',
};

function stub(name: string, props: string[]): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'update:start', 'update:end'],
    name,
    props,
    template: '<div />',
  };
}

type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function validatorAccount(): BlockchainAccount {
  return {
    chain: Blockchain.ETH2,
    data: {
      index: VALIDATOR.index,
      publicKey: VALIDATOR.publicKey,
      status: 'active',
      type: 'validator',
      withdrawalAddress: WITHDRAWAL_ADDRESS,
    },
    nativeAsset: 'ETH',
  };
}

describe('history/events/tx/RepullingEthStakingForm.vue', () => {
  let pinia: Pinia;
  let harness: ModelFormHarness<RepullingEthStakingPayload>;

  function basePayload(): RepullingEthStakingPayload {
    return {
      entryType: OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      fromTimestamp: 1600000000,
      toTimestamp: 1700000000,
    };
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    // The validator list the form offers is derived from these accounts, not set on its own store.
    useBlockchainAccountsStore().updateAccounts(Blockchain.ETH2, [validatorAccount()]);
    vi.useFakeTimers();
  });

  afterEach(() => {
    harness?.wrapper.unmount();
    vi.useRealTimers();
  });

  function createWrapper(payload: RepullingEthStakingPayload = basePayload()): ModelFormHarness<RepullingEthStakingPayload> {
    return mountModelForm(RepullingEthStakingForm, {
      errors: {},
      global: {
        plugins: [pinia],
        stubs: {
          AccountDisplay: stub('AccountDisplay', ['account']),
          DateTimeRangePicker: stub('DateTimeRangePicker', ['start', 'end', 'startErrorMessages', 'endErrorMessages']),
          RuiAlert: stub('RuiAlert', ['type']),
          RuiAutoComplete: stub('RuiAutoComplete', ['modelValue', 'options', 'errorMessages']),
          ValidatorFilterInput: stub('ValidatorFilterInput', ['modelValue', 'items', 'hint']),
        },
      },
      payload,
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return harness.wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function picker(): VueWrapper<StubInstance> {
    return harness.wrapper.findComponent<StubInstance>({ name: 'DateTimeRangePicker' });
  }

  async function choose(testId: string, value: unknown): Promise<void> {
    field(testId).vm.$emit('update:modelValue', value);
    await vi.advanceTimersToNextTimerAsync();
  }

  async function chooseValidator(): Promise<void> {
    harness.wrapper.findComponent<StubInstance>({ name: 'ValidatorFilterInput' }).vm.$emit('update:modelValue', [VALIDATOR]);
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should accept the payload it opens on', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(true);
  });

  it('should reject a payload with no entry type', async () => {
    harness = createWrapper({ ...basePayload(), entryType: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(false);
  });

  it.each([
    ['fromTimestamp'],
    ['toTimestamp'],
  ] as const)('should reject withdrawals with no %s', async (key) => {
    harness = createWrapper({ ...basePayload(), [key]: undefined });
    await vi.advanceTimersToNextTimerAsync();

    expect(await harness.validate()).toBe(false);
  });

  it('should show the message for a cleared start date', async () => {
    harness = createWrapper({ ...basePayload(), fromTimestamp: undefined });
    await vi.advanceTimersToNextTimerAsync();

    await harness.validate();
    await vi.advanceTimersToNextTimerAsync();

    const value: unknown = picker().props('startErrorMessages');
    assert(Array.isArray(value));
    expect(value).not.toEqual([]);
  });

  // Block productions are fetched whole rather than over a range, so the picker goes away and its
  // rules go with it.
  it('should drop the range and its rules for block productions', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await choose('eth-staking-entry-type', OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS);

    expect(picker().exists()).toBe(false);
    expect(harness.model().fromTimestamp).toBeUndefined();
    expect(harness.model().toTimestamp).toBeUndefined();
    expect(await harness.validate()).toBe(true);
  });

  it('should send the chosen validators and no addresses', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await chooseValidator();

    expect(harness.model().validatorIndices).toEqual([VALIDATOR.index]);
    expect(harness.model().addresses).toBeUndefined();
  });

  it('should send the chosen addresses and no validators', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await choose('eth-staking-filter-mode', 'addresses');
    await choose('eth-staking-addresses', [WITHDRAWAL_ADDRESS]);

    expect(harness.model().addresses).toEqual([WITHDRAWAL_ADDRESS]);
    expect(harness.model().validatorIndices).toBeUndefined();
  });

  it('should drop a selection made under the other filter mode', async () => {
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await chooseValidator();
    await choose('eth-staking-filter-mode', 'addresses');

    expect(harness.model().addresses).toEqual([]);
    expect(harness.model().validatorIndices).toBeUndefined();
  });

  it('should not arm the close prompt before anything is edited', async () => {
    harness = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(harness.stateUpdated()).toBe(false);
  });

  /*
   * The selection is not validated, but it is still an edit. The dirty set is wider than the
   * validated one here, which is the only form in this group where the two differ.
   */
  it('should arm the close prompt when only the selection changes', async () => {
    harness = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    await chooseValidator();

    expect(harness.stateUpdated()).toBe(true);
  });

  it('should offer nothing to fill in when no validator is tracked', async () => {
    useBlockchainAccountsStore().updateAccounts(Blockchain.ETH2, []);
    harness = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(field('eth-staking-entry-type').exists()).toBe(false);
    expect(harness.wrapper.findComponent({ name: 'RuiAlert' }).exists()).toBe(true);
  });
});
