import type { BlockchainRpcNodeManageState } from '@/modules/settings/types/rpc';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BlockchainRpcNodeFormDialog from '@/modules/settings/general/rpc/BlockchainRpcNodeFormDialog.vue';
import { RPC_SETUP_STATUS, type RpcSetupRow } from '@/modules/settings/general/rpc/providers/use-rpc-provider-setup';

const { addEvmNode, readNodes, retry, rows, run } = vi.hoisted(() => {
  const rows: { value: RpcSetupRow[] } = { value: [] };
  return { addEvmNode: vi.fn(), readNodes: vi.fn(), retry: vi.fn(), rows, run: vi.fn() };
});

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (): Record<string, unknown> => ({
    addEvmNode,
    deleteEvmNode: vi.fn(),
    editEvmNode: vi.fn(),
    fetchEvmNodes: vi.fn().mockResolvedValue([]),
    reConnectNode: vi.fn(),
  }),
}));

vi.mock('@/modules/settings/general/rpc/providers/use-rpc-nodes-by-chain', () => ({
  useRpcNodesByChain: (): Record<string, unknown> => ({ readNodes }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed, toValue } = await import('vue');
  return {
    useSupportedChains: (): Record<string, unknown> => ({
      getChainName: (chain: string): string => chain,
      useChainName: (chain: unknown) => computed(() => String(toValue(chain) ?? '')),
    }),
  };
});

vi.mock('@/modules/settings/general/rpc/providers/use-rpc-provider-setup', async (importOriginal) => {
  const original = await importOriginal<Record<string, unknown>>();
  const { computed, ref } = await import('vue');
  const rowsRef = ref<RpcSetupRow[]>([]);

  // A hoisted holder is a plain object, so back its `value` with a ref the component can see.
  Object.defineProperty(rows, 'value', {
    get: () => rowsRef.value,
    set: (value: RpcSetupRow[]) => {
      rowsRef.value = value;
    },
  });

  return {
    ...original,
    useRpcProviderSetup: (): Record<string, unknown> => ({
      loadExisting: vi.fn(),
      reset: vi.fn(),
      retry,
      rows: rowsRef,
      run,
      running: ref(false),
      stop: vi.fn(),
      summary: computed(() => ({
        added: 0,
        archive: 0,
        failed: rowsRef.value.filter(row => row.status === RPC_SETUP_STATUS.FAILED).length,
        total: rowsRef.value.length,
      })),
    }),
  };
});

const BigDialogStub = {
  emits: ['confirm', 'cancel'],
  props: ['display', 'action'],
  template: `<div v-if="display">
    <slot />
    <button data-testid="stub-confirm" @click="$emit('confirm')" />
  </div>`,
};

const FormStub = {
  methods: { validate: (): boolean => true },
  template: '<div data-testid="stub-form" />',
};

const CHAINS = [Blockchain.ETH, Blockchain.OPTIMISM, Blockchain.BASE];

function addState(endpoint: string): BlockchainRpcNodeManageState {
  return {
    mode: 'add',
    node: {
      active: true,
      blockchain: Blockchain.ETH,
      endpoint,
      identifier: 0,
      name: 'Infura',
      owned: true,
      weight: 0,
    },
  };
}

function node(endpoint: string): Record<string, unknown> {
  return { active: true, blockchain: Blockchain.OPTIMISM, endpoint, identifier: 1, name: 'Infura', owned: true, weight: 0 };
}

function mountDialog(endpoint: string): VueWrapper {
  return mount(BlockchainRpcNodeFormDialog, {
    global: {
      plugins: [createCustomPinia()],
      stubs: { BigDialog: BigDialogStub, BlockchainRpcNodeForm: FormStub, ChainIcon: true },
    },
    props: { chains: CHAINS, modelValue: addState(endpoint) },
  });
}

async function optIn(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=provider-fan-out-enable] input').setValue(true);
  await flushPromises();
}

describe('modules/settings/general/rpc/BlockchainRpcNodeFormDialog.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    addEvmNode.mockResolvedValue(true);
    readNodes.mockResolvedValue({ nodes: {}, unreadable: [] });
    rows.value = [];
  });

  it('should offer the other chains only for a recognised provider', () => {
    expect(mountDialog('https://eth.example/rpc').find('[data-testid=provider-fan-out-offer]').exists()).toBe(false);
    expect(mountDialog('https://mainnet.infura.io/v3/abcdef').find('[data-testid=provider-fan-out-offer]').exists()).toBe(true);
  });

  it('should add only the chain on screen when the offer is left alone', async () => {
    const wrapper = mountDialog('https://mainnet.infura.io/v3/abcdef');

    await wrapper.find('[data-testid=stub-confirm]').trigger('click');
    await flushPromises();

    expect(addEvmNode).toHaveBeenCalledOnce();
    expect(run).not.toHaveBeenCalled();
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([undefined]);
  });

  it('should walk the other chains once the user opts in', async () => {
    const wrapper = mountDialog('https://mainnet.infura.io/v3/abcdef');
    await optIn(wrapper);

    await wrapper.find('[data-testid=stub-confirm]').trigger('click');
    await flushPromises();

    expect(addEvmNode).toHaveBeenCalledOnce();
    expect(run).toHaveBeenCalledWith([
      expect.objectContaining({ chain: Blockchain.OPTIMISM }),
      expect.objectContaining({ chain: Blockchain.BASE }),
    ]);
    expect(wrapper.find('[data-testid=provider-summary]').exists()).toBe(true);
  });

  it('should not walk the other chains when the node itself could not be added', async () => {
    addEvmNode.mockRejectedValue(new Error('already exists'));
    const wrapper = mountDialog('https://mainnet.infura.io/v3/abcdef');
    await optIn(wrapper);

    await wrapper.find('[data-testid=stub-confirm]').trigger('click');
    await flushPromises();

    expect(run).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=stub-form]').exists()).toBe(true);
  });

  it('should keep the dialog open on the results, and close it on cancel', async () => {
    const wrapper = mountDialog('https://mainnet.infura.io/v3/abcdef');
    await optIn(wrapper);

    await wrapper.find('[data-testid=stub-confirm]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid=stub-form]').exists()).toBe(false);
    expect(wrapper.emitted('complete')).toHaveLength(2);
  });

  it('should not offer the other chains while editing a node', () => {
    const wrapper = mount(BlockchainRpcNodeFormDialog, {
      global: {
        plugins: [createCustomPinia()],
        stubs: { BigDialog: BigDialogStub, BlockchainRpcNodeForm: FormStub, ChainIcon: true },
      },
      props: {
        chains: CHAINS,
        modelValue: { ...addState('https://mainnet.infura.io/v3/abcdef'), mode: 'edit' },
      },
    });

    expect(wrapper.find('[data-testid=provider-fan-out-offer]').exists()).toBe(false);
  });

  it('should just close when every other chain already holds the key', async () => {
    readNodes.mockResolvedValue({
      nodes: {
        [Blockchain.BASE]: [node('https://base-mainnet.infura.io/v3/abcdef')],
        [Blockchain.OPTIMISM]: [node('https://optimism-mainnet.infura.io/v3/abcdef')],
      },
      unreadable: [],
    });
    const wrapper = mountDialog('https://mainnet.infura.io/v3/abcdef');
    await optIn(wrapper);

    await wrapper.find('[data-testid=stub-confirm]').trigger('click');
    await flushPromises();

    expect(addEvmNode).toHaveBeenCalledOnce();
    expect(run).not.toHaveBeenCalled();
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([undefined]);
  });

  it('should walk only the chains that failed when the run is retried', async () => {
    const wrapper = mountDialog('https://mainnet.infura.io/v3/abcdef');
    await optIn(wrapper);

    await wrapper.find('[data-testid=stub-confirm]').trigger('click');
    await flushPromises();

    rows.value = [
      { chain: Blockchain.OPTIMISM, endpoint: 'o', name: 'Infura', status: RPC_SETUP_STATUS.ADDED },
      { chain: Blockchain.BASE, endpoint: 'b', error: 'nope', name: 'Infura', status: RPC_SETUP_STATUS.FAILED },
    ];
    await nextTick();
    await wrapper.find('[data-testid=stub-confirm]').trigger('click');
    await flushPromises();

    expect(retry).toHaveBeenCalledWith([expect.objectContaining({ chain: Blockchain.BASE })]);
    expect(addEvmNode).toHaveBeenCalledOnce();
  });
});
