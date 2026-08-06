import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import BlockchainRpcNodeForm from '@/modules/settings/general/rpc/BlockchainRpcNodeForm.vue';
import { type BlockchainRpcNode, type BlockchainRpcNodeManageState, getPlaceholderNode } from '@/modules/settings/types/rpc';

type FormInstance = InstanceType<typeof BlockchainRpcNodeForm>;

describe('settings/general/rpc/BlockchainRpcNodeForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<FormInstance>;

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function stateFor(node: Partial<BlockchainRpcNode> = {}): BlockchainRpcNodeManageState {
    return {
      mode: 'add',
      node: {
        ...getPlaceholderNode(Blockchain.ETH),
        endpoint: 'https://node.example.com',
        name: 'my node',
        weight: 50,
        ...node,
      },
    };
  }

  function createWrapper(
    modelValue: BlockchainRpcNodeManageState = stateFor(),
    errorMessages: ValidationErrors = {},
  ): VueWrapper<FormInstance> {
    return mount(BlockchainRpcNodeForm, {
      global: {
        plugins: [pinia],
      },
      props: {
        'errorMessages': errorMessages,
        'modelValue': modelValue,
        'onUpdate:errorMessages': async (value: ValidationErrors): Promise<void> => wrapper.setProps({ errorMessages: value }),
        'onUpdate:modelValue': async (value: BlockchainRpcNodeManageState): Promise<void> => wrapper.setProps({ modelValue: value }),
        'onUpdate:stateUpdated': async (value: boolean): Promise<void> => wrapper.setProps({ stateUpdated: value }),
        'stateUpdated': false,
      },
    });
  }

  it('should accept a fully filled node', async () => {
    wrapper = createWrapper();

    expect(wrapper.vm.validate()).toBe(true);
  });

  it('should reject a node without a name', async () => {
    wrapper = createWrapper(stateFor({ name: '' }));

    expect(wrapper.vm.validate()).toBe(false);
    await nextTick();
    expect(wrapper.find('[data-cy=node-name] .details .text-rui-error').exists()).toBe(true);
  });

  it('should reject a node without an endpoint', async () => {
    wrapper = createWrapper(stateFor({ endpoint: '' }));

    expect(wrapper.vm.validate()).toBe(false);
    await nextTick();
    expect(wrapper.find('[data-cy=node-endpoint] .details .text-rui-error').exists()).toBe(true);
  });

  // Etherscan is reached through the api key rather than an endpoint, so it is the one node whose
  // endpoint may stay empty.
  it('should accept an etherscan node without an endpoint', async () => {
    wrapper = createWrapper(stateFor({ endpoint: '', name: 'etherscan' }));

    expect(wrapper.vm.validate()).toBe(true);
  });

  it('should reject a weight above one hundred', async () => {
    wrapper = createWrapper(stateFor({ weight: 101 }));

    expect(wrapper.vm.validate()).toBe(false);
  });

  // The dialog reports the server's rejection after a failed save, which is the only time the form
  // sees external errors.
  it('should display externally reported errors on the field they name', async () => {
    wrapper = createWrapper();

    await wrapper.setProps({ errorMessages: { name: ['Node name already taken'] } });
    await nextTick();
    await nextTick();

    expect(wrapper.find('[data-cy=node-name] .details .text-rui-error').text()).toBe('Node name already taken');
  });

  it('should write an edited name back to the model', async () => {
    wrapper = createWrapper();

    await wrapper.find('[data-cy=node-name] input').setValue('renamed node');

    expect(wrapper.props('modelValue').node.name).toBe('renamed node');
  });

  it('should report the state as updated once a field is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.props('stateUpdated')).toBe(false);

    await wrapper.find('[data-cy=node-name] input').setValue('renamed node');
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.props('stateUpdated')).toBe(true);
  });
});
