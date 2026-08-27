import type { WalletBridgeRequest } from '@shared/wallet-bridge-types';
import type { EIP1193Provider } from '@/types';
import {
  BRIDGE_ERROR_CODES,
  BRIDGE_NOTIFICATION_TYPES,
  ROTKI_RPC_RESPONSES,
  WALLET_EVENT_TYPES,
} from '@shared/proxy/constants';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { ref } from 'vue';
import { useBridgeLogging } from '@/modules/wallet/bridge/use-bridge-logging';
import { useWalletConnectionState } from '@/modules/wallet/bridge/use-wallet-connection-state';
import { useUnifiedProviders } from '../providers/use-unified-providers';
import { useBridgeMessageHandlers } from './use-bridge-message-handlers';

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('../providers/use-unified-providers', () => ({ useUnifiedProviders: vi.fn() }));
vi.mock('@/modules/wallet/bridge/use-bridge-logging', () => ({ useBridgeLogging: vi.fn() }));
vi.mock('@/modules/wallet/bridge/use-wallet-connection-state', () => ({ useWalletConnectionState: vi.fn() }));

function makeRequest(method: string, params?: unknown[], id: string | number = 1): WalletBridgeRequest {
  return { id, jsonrpc: '2.0', method, params };
}

const activeProvider = ref<EIP1193Provider>();
const selectedProviderMetadata = ref<{ name: string; uuid: string }>();
const selectedProviderUuid = ref<string>();
let providerChangedCb: ((newProvider: EIP1193Provider | undefined, oldProvider: EIP1193Provider | undefined) => void) | undefined;
let addLog: Mock;
let trackAccountsRequest: Mock;
let detectProviders: Mock;
let selectProvider: Mock;

interface MockProvider extends EIP1193Provider {
  on: Mock;
  removeListener: Mock;
  request: Mock;
  initialize?: Mock;
}

function makeProvider(overrides: Partial<MockProvider> = {}): MockProvider {
  return {
    on: vi.fn(),
    removeListener: vi.fn(),
    request: vi.fn(async () => '0x1'),
    ...overrides,
  };
}

describe('modules/wallet/bridge/use-bridge-message-handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(activeProvider, undefined);
    set(selectedProviderMetadata, undefined);
    set(selectedProviderUuid, undefined);
    providerChangedCb = undefined;
    addLog = vi.fn();
    trackAccountsRequest = vi.fn(async (promise: Promise<unknown>) => promise);
    detectProviders = vi.fn(async () => []);
    selectProvider = vi.fn(async () => true);

    vi.mocked(useUnifiedProviders).mockReturnValue(createMock<ReturnType<typeof useUnifiedProviders>>({
      activeProvider,
      detectProviders,
      onProviderChanged: vi.fn((cb): (() => void) => {
        providerChangedCb = cb;
        return () => {};
      }),
      selectedProviderMetadata,
      selectedProviderUuid,
      selectProvider,
    }));
    vi.mocked(useBridgeLogging).mockReturnValue(createMock<ReturnType<typeof useBridgeLogging>>({ addLog }));
    vi.mocked(useWalletConnectionState).mockReturnValue(createMock<ReturnType<typeof useWalletConnectionState>>({ trackAccountsRequest }));
  });

  describe('rotki rpc methods', () => {
    it('should answer a ping with pong', async () => {
      const { handleRequest } = useBridgeMessageHandlers();
      const response = await handleRequest(makeRequest('rotki_ping'));
      expect(response).toEqual({ id: 1, jsonrpc: '2.0', result: ROTKI_RPC_RESPONSES.PONG });
    });

    it('should return the serialized available providers', async () => {
      detectProviders.mockResolvedValue([
        { info: { name: 'MetaMask', uuid: 'u1' }, isConnected: true, lastSeen: 5, provider: {}, source: 'eip6963' },
      ]);
      const { handleRequest } = useBridgeMessageHandlers();
      const response = await handleRequest(makeRequest('rotki_getAvailableProviders'));

      expect(response.result).toEqual([
        { info: { name: 'MetaMask', uuid: 'u1' }, isConnected: true, lastSeen: 5, source: 'eip6963' },
      ]);
      expect(addLog).toHaveBeenCalledWith('The app asked for the available providers: 1', 'info');
    });

    it('should return the selected provider detail when one is set', async () => {
      set(activeProvider, makeProvider());
      set(selectedProviderMetadata, { name: 'MetaMask', uuid: 'u1' });
      set(selectedProviderUuid, 'u1');
      const { handleRequest } = useBridgeMessageHandlers();

      const response = await handleRequest(makeRequest('rotki_getSelectedProvider'));
      expect(response.result).toEqual({ info: { name: 'MetaMask', uuid: 'u1' }, provider: {} });
    });

    it('should return null when no provider is selected', async () => {
      const { handleRequest } = useBridgeMessageHandlers();
      const response = await handleRequest(makeRequest('rotki_getSelectedProvider'));
      expect(response.result).toBeNull();
    });

    it('should reject a select-provider call without a uuid', async () => {
      const { handleRequest } = useBridgeMessageHandlers();
      const response = await handleRequest(makeRequest('rotki_selectProvider', []));
      expect(response.error?.code).toBe(BRIDGE_ERROR_CODES.INVALID_PARAMS);
      expect(selectProvider).not.toHaveBeenCalled();
    });

    it('should select the provider and focus the window', async () => {
      const focusSpy = vi.spyOn(window, 'focus').mockImplementation(() => {});
      const { handleRequest } = useBridgeMessageHandlers();

      const response = await handleRequest(makeRequest('rotki_selectProvider', ['u1']));
      expect(selectProvider).toHaveBeenCalledWith('u1');
      expect(response.result).toBe(true);
      expect(focusSpy).toHaveBeenCalled();
    });
  });

  describe('standard rpc methods', () => {
    it('should error when no provider is available', async () => {
      const { handleRequest } = useBridgeMessageHandlers();
      const response = await handleRequest(makeRequest('eth_chainId'));
      expect(response.error?.code).toBe(BRIDGE_ERROR_CODES.NO_PROVIDER);
      expect(response.error?.message).toBe('No browser wallet provider found');
    });

    it('should forward a standard request to the provider', async () => {
      const provider = makeProvider({ request: vi.fn(async () => '0x89') });
      set(activeProvider, provider);
      const { handleRequest } = useBridgeMessageHandlers();

      const response = await handleRequest(makeRequest('eth_chainId', ['a']));
      expect(provider.request).toHaveBeenCalledWith({ method: 'eth_chainId', params: ['a'] });
      expect(response.result).toBe('0x89');
    });

    it('should initialize the provider and track eth_requestAccounts', async () => {
      const initialize = vi.fn(async () => {});
      const provider = makeProvider({ initialize, request: vi.fn(async () => ['0xabc']) });
      set(activeProvider, provider);
      const { handleRequest } = useBridgeMessageHandlers();

      const response = await handleRequest(makeRequest('eth_requestAccounts'));
      expect(initialize).toHaveBeenCalledTimes(1);
      expect(trackAccountsRequest).toHaveBeenCalledTimes(1);
      expect(response.result).toEqual(['0xabc']);
    });

    it('should retry the first eth_requestAccounts after a 4001 error', async () => {
      vi.useFakeTimers();
      const request = vi.fn()
        .mockRejectedValueOnce(Object.assign(new Error('rejected'), { code: 4001 }))
        .mockResolvedValueOnce(['0xabc']);
      const provider = makeProvider({ request });
      set(activeProvider, provider);
      const { handleRequest } = useBridgeMessageHandlers();

      const promise = handleRequest(makeRequest('eth_requestAccounts'));
      await vi.advanceTimersByTimeAsync(600);
      const response = await promise;

      expect(request).toHaveBeenCalledTimes(2);
      expect(response.result).toEqual(['0xabc']);
      vi.useRealTimers();
    });

    it('should map a provider error into an error response', async () => {
      const request = vi.fn(async () => {
        throw Object.assign(new Error('boom'), { code: -32000, data: { info: 'x' } });
      });
      set(activeProvider, makeProvider({ request }));
      const { handleRequest } = useBridgeMessageHandlers();

      const response = await handleRequest(makeRequest('eth_call'));
      expect(response.error).toEqual({ code: -32000, data: { info: 'x' }, message: 'boom' });
    });
  });

  describe('wallet event forwarding', () => {
    it('should register listeners and forward provider events when the provider changes', () => {
      const sendMessage = vi.fn();
      const newProvider = makeProvider();
      useBridgeMessageHandlers(sendMessage);

      expect(providerChangedCb).toBeDefined();
      providerChangedCb!(newProvider, undefined);

      // one listener per wallet event type
      expect(newProvider.on).toHaveBeenCalledTimes(4);

      const call = newProvider.on.mock.calls.find(([type]) => type === WALLET_EVENT_TYPES.ACCOUNTS_CHANGED);
      const listener = call?.[1];
      listener(['0xabc']);

      expect(sendMessage).toHaveBeenCalledWith({
        eventData: ['0xabc'],
        eventName: WALLET_EVENT_TYPES.ACCOUNTS_CHANGED,
        type: BRIDGE_NOTIFICATION_TYPES.WALLET_EVENT,
      });
    });

    it('should clean up the previous provider listeners on change', () => {
      const oldProvider = makeProvider();
      const newProvider = makeProvider();
      useBridgeMessageHandlers(vi.fn());

      providerChangedCb!(oldProvider, undefined); // registers on oldProvider
      providerChangedCb!(newProvider, oldProvider); // should clean old, register new

      expect(oldProvider.removeListener).toHaveBeenCalledTimes(4);
      expect(newProvider.on).toHaveBeenCalledTimes(4);
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });
});
