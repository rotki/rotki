import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { AddTransactionHashPayload } from '@/modules/history/events/event-payloads';
import { Blockchain } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, defineComponent, useTemplateRef } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import TransactionForm from '@/modules/history/events/tx/TransactionForm.vue';
import '@test/i18n';

const ADDRESS = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12';
const TX_HASH = '0x8d0e0f0e0a4b1e1c9c8d6c5b4a39281706f5e4d3c2b1a09f8e7d6c5b4a392817';
const OTHER_TX_HASH = '0x1a2b3c4d5e6f78901234567890abcdef1234567890abcdef1234567890abcdef';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    evmAndEvmLikeTxChainsInfo: computed(() => [{ id: Blockchain.ETH }, { id: Blockchain.OPTIMISM }]),
    getChain: (chain: string): string => chain,
    solanaChainsData: computed(() => []),
  }),
}));

/** The two selects are heavy third-party wrappers, stubbed down to what the form reads. */
function selectStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'items', 'chains'],
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

/**
 * The form edits a payload its dialog owns, so the round trip is part of what is under test: a
 * harness that holds the model in a real ref exercises it, while re-feeding props by hand does not.
 */
let seed: { errors: ValidationErrors; payload: AddTransactionHashPayload };

const Harness = defineComponent({
  components: { TransactionForm },
  setup() {
    const model = ref<AddTransactionHashPayload>(seed.payload);
    const errors = ref<ValidationErrors>(seed.errors);
    const stateUpdated = ref<boolean>(false);
    const form = useTemplateRef<InstanceType<typeof TransactionForm>>('form');
    return { errors, form, model, stateUpdated };
  },
  template: `<TransactionForm
    ref="form"
    v-model="model"
    v-model:error-messages="errors"
    v-model:state-updated="stateUpdated"
  />`,
});

describe('history/events/tx/TransactionForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof Harness>>;

  function basePayload(): AddTransactionHashPayload {
    return {
      associatedAddress: ADDRESS,
      blockchain: Blockchain.ETH,
      txRef: TX_HASH,
    };
  }

  beforeEach(() => {
    localStorage.clear();
    pinia = createPinia();
    setActivePinia(pinia);
    const store = useBlockchainAccountsStore();
    store.updateAccounts(Blockchain.ETH, [addressAccount(Blockchain.ETH, ADDRESS)]);
    store.updateAccounts(Blockchain.OPTIMISM, [addressAccount(Blockchain.OPTIMISM, ADDRESS)]);
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    modelValue: AddTransactionHashPayload = basePayload(),
    errorMessages: ValidationErrors = {},
  ): VueWrapper<InstanceType<typeof Harness>> {
    seed = { errors: errorMessages, payload: modelValue };
    return mount(Harness, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
        stubs: {
          BlockchainAccountSelector: selectStub('BlockchainAccountSelector'),
          ChainSelect: selectStub('ChainSelect'),
        },
      },
    });
  }

  function form(): InstanceType<typeof TransactionForm> {
    const instance = wrapper.vm.form;
    assert(instance);
    return instance;
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function editTxRef(value: string): Promise<void> {
    await field('tx-ref').find('input').setValue(value);
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should accept a fully filled payload', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await form().validate()).toBe(true);
  });

  it.each([
    ['associatedAddress'],
    ['txRef'],
  ] as const)('should reject a payload with an empty %s', async (key) => {
    wrapper = createWrapper({ ...basePayload(), [key]: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await form().validate()).toBe(false);
  });

  // The form seeds a chain on open, so an empty `blockchain` is only reachable by clearing the
  // select, never by opening the dialog on a payload that has none.
  it('should reject the payload once the chain is cleared', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    field('tx-blockchain').vm.$emit('update:modelValue', '');
    await vi.advanceTimersToNextTimerAsync();

    expect(await form().validate()).toBe(false);
    await vi.advanceTimersToNextTimerAsync();
    expect(messages('tx-blockchain')).not.toEqual([]);
  });

  it('should reject a tx reference that is not a hash or a signature', async () => {
    wrapper = createWrapper({ ...basePayload(), txRef: '0xnope' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await form().validate()).toBe(false);
  });

  it('should reject a whitespace-only tx reference', async () => {
    wrapper = createWrapper({ ...basePayload(), txRef: '   ' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await form().validate()).toBe(false);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ associatedAddress: '', blockchain: '', txRef: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('tx-account')).toEqual([]);
    expect(messages('tx-blockchain')).toEqual([]);
  });

  it('should reveal every message once validate runs', async () => {
    wrapper = createWrapper({ associatedAddress: '', blockchain: '', txRef: '' });
    await vi.advanceTimersToNextTimerAsync();

    await form().validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('tx-account')).toEqual(['transactions.form.account.validation.non_empty']);
    expect(field('tx-ref').find('.text-rui-error').exists()).toBe(true);
  });

  it('should show the tx reference message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await editTxRef('');

    expect(field('tx-ref').find('.text-rui-error').exists()).toBe(true);
    // The untouched fields stay quiet.
    expect(messages('tx-account')).toEqual([]);
  });

  it('should write an edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await editTxRef(OTHER_TX_HASH);

    expect(wrapper.vm.model.txRef).toBe(OTHER_TX_HASH);
  });

  it('should surface a server error under the field it names', async () => {
    wrapper = createWrapper(basePayload(), { txRef: ['already added'] });
    await vi.advanceTimersToNextTimerAsync();

    await form().validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(field('tx-ref').text()).toContain('already added');
  });

  it('should seed the chain remembered from the last add', async () => {
    localStorage.setItem('rotki.history_event.add_by_tx_hash.chain', Blockchain.OPTIMISM);
    wrapper = createWrapper({ ...basePayload(), blockchain: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.vm.model.blockchain).toBe(Blockchain.OPTIMISM);
  });

  it('should not arm the close prompt for the chain it seeds itself', async () => {
    wrapper = createWrapper({ ...basePayload(), blockchain: '' });
    // Past the point where an edit would be picked up, so only the seeding is in play.
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.vm.stateUpdated).toBe(false);
  });

  it('should arm the close prompt once a field is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    await editTxRef(OTHER_TX_HASH);

    expect(wrapper.vm.stateUpdated).toBe(true);
  });

  it('should render nothing to fill in when no chain has an account', async () => {
    const store = useBlockchainAccountsStore();
    store.updateAccounts(Blockchain.ETH, []);
    store.updateAccounts(Blockchain.OPTIMISM, []);
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(field('tx-blockchain').exists()).toBe(false);
    expect(wrapper.text()).toContain('transactions.form.no_accounts');
  });
});
