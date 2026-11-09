import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ElectronConnectionStatus from './ElectronConnectionStatus.vue';
import { BridgeConnectionPhase, type BridgeConnectionState } from './use-wallet-proxy-client';

const onRetryConnection = vi.fn<() => void>();
const onDisconnect = vi.fn<() => void>();

function mountWith(state: BridgeConnectionState, error?: string): VueWrapper {
  return mount(ElectronConnectionStatus, { props: { error, onDisconnect, onRetryConnection, state } });
}

function textOf(wrapper: VueWrapper, testId: string): string {
  return wrapper.find(`[data-testid="${testId}"]`).text();
}

describe('modules/wallet/bridge/ElectronConnectionStatus', () => {
  it('should disconnect from the button while connected', async () => {
    const wrapper = mountWith({ phase: BridgeConnectionPhase.connected });

    await wrapper.find('[data-testid="bridge-connection-disconnect"]').trigger('click');

    expect(onDisconnect).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-testid="bridge-connection-connect"]').exists()).toBe(false);
  });

  it('should label a first connect as connecting and disable the button', () => {
    const wrapper = mountWith({ attempt: 0, phase: BridgeConnectionPhase.connecting });

    expect(textOf(wrapper, 'bridge-connection-label')).toContain('connecting_to_electron');
    expect(wrapper.find('[data-testid="bridge-connection-connect"]').attributes('disabled')).toBeDefined();
  });

  it.each<BridgeConnectionState>([
    { attempt: 2, phase: BridgeConnectionPhase.connecting },
    { attempt: 2, phase: BridgeConnectionPhase.retryWaiting },
  ])('should read as reconnecting without showing the error in $phase', (state) => {
    const wrapper = mountWith(state, 'WebSocket connection error');

    expect(textOf(wrapper, 'bridge-connection-label')).toContain('reconnecting_to_electron');
    expect(wrapper.find('[data-testid="bridge-connection-error"]').exists()).toBe(false);
  });

  it('should show the error and offer a retry once retries are exhausted', async () => {
    const wrapper = mountWith({ phase: BridgeConnectionPhase.retriesExhausted }, 'WebSocket connection error');

    expect(textOf(wrapper, 'bridge-connection-message')).toContain('electron_retries_exhausted_message');
    expect(textOf(wrapper, 'bridge-connection-error')).toContain('WebSocket connection error');

    await wrapper.find('[data-testid="bridge-connection-connect"]').trigger('click');
    expect(onRetryConnection).toHaveBeenCalledTimes(1);
  });

  it('should read as disconnected and not exhausted after a manual disconnect', () => {
    const wrapper = mountWith({ phase: BridgeConnectionPhase.disconnected });

    expect(textOf(wrapper, 'bridge-connection-label')).toContain('disconnected_from_electron');
    expect(textOf(wrapper, 'bridge-connection-message')).toContain('electron_disconnected_message');
  });
});
