import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BridgeOverlay from '@/modules/wallet/bridge/BridgeOverlay.vue';
import ConnectionLogs from '@/modules/wallet/bridge/ConnectionLogs.vue';
import { installMockWallets } from '@/modules/wallet/bridge/dev-mock-wallets';
import ElectronConnectionStatus from '@/modules/wallet/bridge/ElectronConnectionStatus.vue';
import { BridgeConnectionPhase, type BridgeConnectionState, useWalletProxyClient } from '@/modules/wallet/bridge/use-wallet-proxy-client';
import WalletBridgePage from './index.vue';

const { routeQuery, setConnected } = vi.hoisted(() => {
  const routeQuery: { current: Record<string, string> } = { current: {} };
  return { routeQuery, setConnected: vi.fn<(connected: boolean) => void>() };
});

vi.mock('vue-router', () => ({
  useRoute: (): { query: Record<string, string> } => ({ query: routeQuery.current }),
}));

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: (): { setConnected: typeof setConnected } => ({ setConnected }),
}));

vi.mock('@/modules/wallet/bridge/dev-mock-wallets', () => ({
  installMockWallets: vi.fn<typeof installMockWallets>(),
}));

vi.mock('@/modules/wallet/bridge/use-wallet-proxy-client', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/wallet/bridge/use-wallet-proxy-client')>(),
  useWalletProxyClient: vi.fn(),
}));

const connect = vi.fn<() => void>();
const disconnect = vi.fn<() => void>();
const cleanup = vi.fn<() => void>();
const state = shallowRef<BridgeConnectionState>({ phase: BridgeConnectionPhase.disconnected });
const isConnected = computed<boolean>(() => get(state).phase === BridgeConnectionPhase.connected);
let takeOver: (() => void) | undefined;

function mountPage(): VueWrapper {
  return mount(WalletBridgePage, {
    global: {
      stubs: {
        BridgeOverlay: true,
        ConnectionLogs: true,
        ElectronConnectionStatus: true,
        ProviderSelectionNotification: true,
        RotkiLogo: true,
        WalletAddressIndicator: true,
      },
    },
  });
}

function logMessages(wrapper: VueWrapper): string[] {
  const logs: { message: string }[] = wrapper.findComponent(ConnectionLogs).props('logs');
  return logs.map(log => log.message);
}

describe('pages/wallet-bridge/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    routeQuery.current = {};
    takeOver = undefined;
    set(state, { phase: BridgeConnectionPhase.disconnected });
    vi.mocked(useWalletProxyClient).mockReturnValue({
      cleanup,
      connect,
      disconnect,
      isConnected,
      isConnecting: computed<boolean>(() => false),
      lastError: ref<string>(),
      onTakeOver: (callback: () => void): void => {
        takeOver = callback;
      },
      state,
    });
  });

  it('should connect to rotki on mount and clean up on unmount', () => {
    const wrapper = mountPage();
    expect(connect).toHaveBeenCalledTimes(1);
    expect(setConnected).toHaveBeenCalledWith(true);
    expect(cleanup).not.toHaveBeenCalled();

    wrapper.unmount();
    expect(cleanup).toHaveBeenCalledTimes(1);
  });

  it('should log a first connect and a retry differently, with the attempt number', async () => {
    const wrapper = mountPage();

    set(state, { attempt: 0, phase: BridgeConnectionPhase.connecting });
    await nextTick();
    set(state, { attempt: 1, phase: BridgeConnectionPhase.retryWaiting });
    await nextTick();
    set(state, { attempt: 1, phase: BridgeConnectionPhase.connecting });
    await nextTick();

    const messages = logMessages(wrapper);
    expect(messages).toHaveLength(2);
    expect(messages[0]).toContain('attempt 2 of 5');
    expect(messages[1]).toContain('Attempting to connect');
  });

  it('should log when the connection opens and when it is lost', async () => {
    const wrapper = mountPage();

    set(state, { phase: BridgeConnectionPhase.connected });
    await nextTick();
    expect(logMessages(wrapper)[0]).toContain('Successfully connected');

    set(state, { phase: BridgeConnectionPhase.disconnected });
    await nextTick();
    expect(logMessages(wrapper)[0]).toContain('connection to Electron app lost');
  });

  it('should show the overlay only after another bridge takes over', async () => {
    const wrapper = mountPage();
    expect(wrapper.findComponent(BridgeOverlay).exists()).toBe(false);

    takeOver?.();
    await nextTick();

    expect(wrapper.findComponent(BridgeOverlay).exists()).toBe(true);
    expect(logMessages(wrapper)[0]).toBe('Another bridge is now active');
  });

  it('should pass the state on, and wire the status actions to the client', async () => {
    set(state, { phase: BridgeConnectionPhase.retriesExhausted });
    const wrapper = mountPage();
    const status = wrapper.findComponent(ElectronConnectionStatus);
    expect(status.props('state')).toEqual({ phase: BridgeConnectionPhase.retriesExhausted });
    connect.mockClear();

    status.props('onRetryConnection')();
    await nextTick();
    expect(connect).toHaveBeenCalledTimes(1);
    expect(logMessages(wrapper)[0]).toContain('Retrying connection');

    status.props('onDisconnect')();
    expect(disconnect).toHaveBeenCalledTimes(1);
  });

  describe('dev mock wallets', () => {
    it('should not install any without the query parameter', async () => {
      mountPage();
      await flushPromises();

      expect(installMockWallets).not.toHaveBeenCalled();
    });

    it('should install the requested number', async () => {
      routeQuery.current = { mockWallets: '2' };
      mountPage();
      await flushPromises();

      expect(installMockWallets).toHaveBeenCalledExactlyOnceWith({ count: 2, rejects: false });
    });

    it('should make them reject when asked to', async () => {
      routeQuery.current = { mockWallets: '1', mockWalletsReject: '' };
      mountPage();
      await flushPromises();

      expect(installMockWallets).toHaveBeenCalledExactlyOnceWith({ count: 1, rejects: true });
    });
  });
});
