import type { EIP1193EventName, EIP1193Provider, EIP1193ProviderEvents, RpcRequest } from '@/types';
import { defaultWindow } from '@vueuse/core';
import { logger } from '@/modules/core/common/logging/logging';

/**
 * An EIP-1193 provider that talks through the preload `walletBridge`.
 *
 * @remarks
 * The listener list lives here in the renderer rather than across the context bridge. A function
 * sent over that bridge arrives as a different reference each time, so the bridge itself could
 * never match a listener back to the one that registered it, and removal would silently do
 * nothing. Only one forwarder per event type is registered on the bridge; this map fans it out.
 *
 * @returns undefined outside Electron, where there is no bridge to proxy.
 */
export function useProxyProvider(): EIP1193Provider | undefined {
  const walletBridge = defaultWindow?.walletBridge;
  if (!walletBridge) {
    return undefined;
  }

  logger.debug('Creating proxy provider from wallet bridge');

  const eventListeners = new Map<EIP1193EventName, ((...args: any[]) => void)[]>();

  onScopeDispose(() => {
    for (const event of eventListeners.keys())
      walletBridge.removeEventListener(event);

    eventListeners.clear();
  }, true);

  const proxyProvider: EIP1193Provider = {
    get connected(): boolean {
      return walletBridge?.isEnabled() && walletBridge?.isConnected();
    },

    disconnect: async (): Promise<void> => {
      await walletBridge.disable();
    },

    isRotkiBridge: true,

    off: <K extends EIP1193EventName>(
      event: K,
      callback: (...args: EIP1193ProviderEvents[K]) => void,
    ) => {
      proxyProvider.removeListener!(event, callback);
    },

    on: <K extends EIP1193EventName>(
      event: K,
      callback: (...args: EIP1193ProviderEvents[K]) => void,
    ) => {
      if (!eventListeners.has(event)) {
        eventListeners.set(event, []);

        walletBridge.addEventListener(event, (data: any) => {
          const listeners = eventListeners.get(event) ?? [];
          listeners.forEach((listener) => {
            try {
              if (event === 'disconnect' && !data) {
                listener();
              }
              else {
                listener(data);
              }
            }
            catch (error) {
              logger.error(`Error in ${event} listener:`, error);
            }
          });
        });
      }

      const listeners = eventListeners.get(event)!;
      listeners.push(callback);
    },

    removeListener: <K extends EIP1193EventName>(
      event: K,
      callback: (...args: EIP1193ProviderEvents[K]) => void,
    ) => {
      const listeners = eventListeners.get(event);
      if (listeners) {
        const index = listeners.indexOf(callback);
        if (index !== -1) {
          listeners.splice(index, 1);

          if (listeners.length === 0) {
            walletBridge.removeEventListener(event);
            eventListeners.delete(event);
          }
        }
      }
    },

    request: async <T = unknown>(request: RpcRequest): Promise<T> => walletBridge.request(request),
  };

  logger.debug('Proxy provider created successfully');
  return proxyProvider;
}
