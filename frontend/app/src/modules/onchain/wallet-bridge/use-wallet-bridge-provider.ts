import type { EIP1193EventName, EIP1193Provider, EIP1193ProviderEvents, RpcRequest } from '@/types';
import { logger } from '@/utils/logging';

/**
 * Sets up window.ethereum provider using the walletBridge API from preload
 * This solves the context bridge function reference issue by managing event listeners in renderer context
 */
export function setupWalletBridgeProvider(): void {
  // Only set up if walletBridge is available and window.ethereum is not already our provider
  const walletBridge = window.walletBridge;
  if (!walletBridge || window.ethereum?.isRotkiBridge) {
    return;
  }

  logger.debug('Setting up wallet bridge provider in renderer context');

  // Event listeners managed purely in renderer context - no context bridge issues
  const eventListeners = new Map<EIP1193EventName, ((...args: any[]) => void)[]>();

  // Create EIP1193Provider implementation
  const walletBridgeProvider: EIP1193Provider = {
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
      // Alias for removeListener
      walletBridgeProvider.removeListener!(event, callback);
    },

    on: <K extends EIP1193EventName>(
      event: K,
      callback: (...args: EIP1193ProviderEvents[K]) => void,
    ) => {
      if (!eventListeners.has(event)) {
        eventListeners.set(event, []);

        // Set up bridge event forwarding for this event type
        walletBridge.addEventListener(event, (data: any) => {
          const listeners = eventListeners.get(event) || [];
          listeners.forEach((listener) => {
            try {
              if (event === 'disconnect' && !data) {
                // Disconnect events don't have data
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
      listeners.push(callback as (...args: any[]) => void);
    },

    removeListener: <K extends EIP1193EventName>(
      event: K,
      callback: (...args: EIP1193ProviderEvents[K]) => void,
    ) => {
      const listeners = eventListeners.get(event);
      if (listeners) {
        const index = listeners.indexOf(callback as (...args: any[]) => void);
        if (index !== -1) {
          listeners.splice(index, 1);

          // If no more listeners for this event, clean up bridge forwarding
          if (listeners.length === 0) {
            walletBridge.removeEventListener(event);
            eventListeners.delete(event);
          }
        }
      }
    },

    request: async <T = unknown>(request: RpcRequest): Promise<T> => walletBridge.request(request) as Promise<T>,
  };

  // Inject the provider
  window.ethereum = walletBridgeProvider;
  logger.debug('Wallet bridge provider installed as window.ethereum');
}
