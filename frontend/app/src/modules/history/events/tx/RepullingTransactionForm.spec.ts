import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { RepullingEthStakingPayload, RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, defineComponent, useTemplateRef } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import RepullingTransactionForm, { type AccountType } from '@/modules/history/events/tx/RepullingTransactionForm.vue';
import '@test/i18n';

const ADDRESS = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12';

vi.mock('@/modules/balances/exchanges/use-exchange-data', () => ({
  useExchangeData: (): Record<string, unknown> => ({
    syncingExchanges: computed(() => [{ location: 'kraken', name: 'my kraken' }]),
  }),
}));

vi.mock('@/modules/history/events/tx/use-repulling-transaction-form', () => ({
  shouldShowDateRangePicker: (): boolean => true,
  useRepullingTransactionForm: (): Record<string, unknown> => ({
    chainOptions: computed<string[]>(() => ['all', Blockchain.ETH]),
    getUsableChains: (): string[] => [Blockchain.ETH],
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

/** The three forms share one payload and one unsaved-changes flag, which is what the tabs switch. */
const Harness = defineComponent({
  components: { RepullingTransactionForm },
  setup() {
    const model = ref<RepullingTransactionPayload>({
      address: '',
      chain: 'all',
      fromTimestamp: 1600000000,
      toTimestamp: 1700000000,
    });
    const ethStakingData = ref<RepullingEthStakingPayload>({
      entryType: OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      fromTimestamp: 1600000000,
      toTimestamp: 1700000000,
    });
    const errors = ref<ValidationErrors>({});
    const stateUpdated = ref<boolean>(false);
    const accountType = ref<AccountType>('blockchain');
    const form = useTemplateRef<InstanceType<typeof RepullingTransactionForm>>('form');
    return { accountType, errors, ethStakingData, form, model, stateUpdated };
  },
  template: `<RepullingTransactionForm
    ref="form"
    v-model="model"
    v-model:account-type="accountType"
    v-model:error-messages="errors"
    v-model:eth-staking-data="ethStakingData"
    v-model:state-updated="stateUpdated"
  />`,
});

describe('history/events/tx/RepullingTransactionForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof Harness>>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    useBlockchainAccountsStore().updateAccounts(Blockchain.ETH, [addressAccount(Blockchain.ETH, ADDRESS)]);
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(): VueWrapper<InstanceType<typeof Harness>> {
    return mount(Harness, {
      global: {
        plugins: [pinia],
        stubs: {
          AccountDisplay: stub('AccountDisplay', ['account']),
          BlockchainAccountSelector: stub('BlockchainAccountSelector', ['modelValue', 'errorMessages', 'chains']),
          ChainSelect: stub('ChainSelect', ['modelValue', 'errorMessages', 'items']),
          DateTimeRangePicker: stub('DateTimeRangePicker', ['start', 'end', 'startErrorMessages', 'endErrorMessages']),
          RuiAlert: stub('RuiAlert', ['type']),
          RuiAutoComplete: stub('RuiAutoComplete', ['modelValue', 'options', 'errorMessages']),
          RuiTab: stub('RuiTab', ['value']),
          RuiTabs: stub('RuiTabs', ['modelValue']),
          ValidatorFilterInput: stub('ValidatorFilterInput', ['modelValue', 'items', 'hint']),
        },
      },
    });
  }

  async function switchTo(type: AccountType): Promise<void> {
    wrapper.vm.accountType = type;
    await vi.advanceTimersToNextTimerAsync();
  }

  async function editChain(): Promise<void> {
    wrapper.findComponent<StubInstance>({ name: 'ChainSelect' }).vm.$emit('update:modelValue', Blockchain.ETH);
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should delegate validation to the tab on screen', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    // The exchange tab opens with nothing chosen, so it rejects where the blockchain tab accepts.
    expect(await wrapper.vm.form?.validate()).toBe(true);

    await switchTo('exchange');

    expect(await wrapper.vm.form?.validate()).toBe(false);
  });

  /*
   * The flag belongs to the dialog and outlives the form that armed it. Leaving a tab has to hand
   * it back disarmed, or the tab arrived at prompts about changes the user made somewhere else -
   * and cannot clear it, because its own state is pristine and never changes.
   */
  it('should disarm the close prompt when an edited tab is left', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await editChain();
    expect(wrapper.vm.stateUpdated).toBe(true);

    await switchTo('exchange');

    expect(wrapper.vm.stateUpdated).toBe(false);
  });

  it('should disarm the close prompt on the way to eth staking too', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await editChain();
    await switchTo('eth_staking');

    expect(wrapper.vm.stateUpdated).toBe(false);
  });
});
