import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { NODE_STATUS, type NodeStatus } from '@/modules/settings/general/rpc/rpc-node-status';
import RpcNodeStatusCell from '@/modules/settings/general/rpc/RpcNodeStatusCell.vue';

interface Props {
  status: NodeStatus;
  active?: boolean;
  cooldownUntil?: number | null;
  reconnecting?: boolean;
}

function mountCell(props: Props): VueWrapper<InstanceType<typeof RpcNodeStatusCell>> {
  return mount(RpcNodeStatusCell, {
    props,
  });
}

describe('modules/settings/general/rpc/RpcNodeStatusCell', () => {
  it('should render the connected badge', () => {
    const wrapper = mountCell({ status: NODE_STATUS.CONNECTED });
    expect(wrapper.text()).toContain('evm_rpc_node_manager.connected.true');
  });

  it('should render the cooling-down badge', () => {
    const wrapper = mountCell({ status: NODE_STATUS.COOLING_DOWN });
    expect(wrapper.text()).toContain('evm_rpc_node_manager.connected.cooling_down');
  });

  it('should render the ready/disconnected badge for the default case', () => {
    const wrapper = mountCell({ status: NODE_STATUS.READY });
    expect(wrapper.text()).toContain('evm_rpc_node_manager.connected.false');
  });

  it('should show the reconnect button only for an active failed node and emit reconnect', async () => {
    const inactive = mountCell({ active: false, status: NODE_STATUS.FAILED });
    expect(inactive.find('button').exists()).toBe(false);

    const wrapper = mountCell({ active: true, status: NODE_STATUS.FAILED });
    await wrapper.find('button').trigger('click');
    expect(wrapper.emitted('reconnect')).toHaveLength(1);
  });
});
