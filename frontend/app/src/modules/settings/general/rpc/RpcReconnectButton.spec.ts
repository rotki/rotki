import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import RpcReconnectButton from '@/modules/settings/general/rpc/RpcReconnectButton.vue';

interface Props {
  tooltip?: string;
  disabled?: boolean;
}

function mountButton(props: Props = {}): VueWrapper<InstanceType<typeof RpcReconnectButton>> {
  return mount(RpcReconnectButton, {
    props: { tooltip: 'Reconnect', ...props },
  });
}

describe('modules/settings/general/rpc/RpcReconnectButton', () => {
  it('should emit reconnect when clicked', async () => {
    const wrapper = mountButton();
    await wrapper.find('button').trigger('click');
    expect(wrapper.emitted('reconnect')).toHaveLength(1);
  });

  it('should be disabled when the disabled prop is set', () => {
    const wrapper = mountButton({ disabled: true });
    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
  });
});
