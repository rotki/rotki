import { startPromise } from '@shared/utils';
import { get, isDefined, set } from '@vueuse/core';
import { computed, onBeforeUnmount, ref } from 'vue';
import { useWalletBridge } from '@/composables/wallet-bridge';
import { waitForCondition } from '@/utils/async-utilities';
import { logger } from '@/utils/logging';
import { PROXY_CONFIG } from './bridge-config';
import { createResourceManager } from './resource-management';

interface ProxyState {
  httpListening: boolean;
  wsListening: boolean;
  clientConnected: boolean;
}

interface UseWalletProxyReturn {
  setupProxy: () => Promise<void>;
  waitForProxyConnection: (timeoutMs?: number, signal?: AbortSignal) => Promise<void>;
  waitForProxyClientReady: (timeoutMs?: number, signal?: AbortSignal) => Promise<void>;
  startConnectionHealthCheck: (isConnected: () => boolean, onDisconnect: () => void) => void;
  stopConnectionHealthCheck: () => void;
  disconnectProxy: () => Promise<void>;
}

export function useWalletProxy(): UseWalletProxyReturn {
  const { isProxyClientConnected, isProxyClientReady, isProxyHttpListening, isProxyWebSocketListening, openProxyPageInDefaultBrowser, proxyStopServers } = useWalletBridge();
  const { cleanupResources: cleanupActiveResources, resources: activeResources } = createResourceManager();

  const healthCheckInterval = ref<NodeJS.Timeout>();
  const isHealthCheckActive = computed<boolean>(() => isDefined(healthCheckInterval));

  const checkProxyState = async (): Promise<ProxyState> => {
    const [httpListening, wsListening, clientConnected] = await Promise.all([
      isProxyHttpListening(),
      isProxyWebSocketListening(),
      isProxyClientConnected(),
    ]);

    const state = { clientConnected, httpListening, wsListening };
    logger.debug('Bridge state check:', {
      client: state.clientConnected ? 'connected' : 'disconnected',
      httpServer: state.httpListening ? 'listening' : 'not listening',
      wsServer: state.wsListening ? 'listening' : 'not listening',
    });

    return state;
  };

  const waitForProxyConnection = async (
    timeoutMs: number = PROXY_CONFIG.CONNECTION_TIMEOUT,
    signal?: AbortSignal,
  ): Promise<void> => {
    await waitForCondition(
      async () => isProxyClientConnected(),
      connected => connected,
      {
        initialDelay: PROXY_CONFIG.BRIDGE_PAGE_DELAY,
        interval: PROXY_CONFIG.RETRY_INTERVAL,
        name: 'bridge connection',
        signal,
        timeout: timeoutMs,
      },
    );
  };

  const waitForProxyClientReady = async (
    timeoutMs: number = PROXY_CONFIG.CONNECTION_TIMEOUT,
    signal?: AbortSignal,
  ): Promise<void> => {
    await waitForCondition(
      async () => isProxyClientReady(),
      ready => ready,
      {
        initialDelay: PROXY_CONFIG.BRIDGE_PAGE_DELAY,
        interval: PROXY_CONFIG.RETRY_INTERVAL,
        name: 'bridge client ready',
        signal,
        timeout: timeoutMs,
      },
    );
  };

  /**
   * Start connection health monitoring
   */
  const startConnectionHealthCheck = (
    isConnected: () => boolean,
    onDisconnect: () => void,
  ): void => {
    // Clear any existing interval
    stopConnectionHealthCheck();

    set(healthCheckInterval, setInterval(() => {
      startPromise(performHealthCheck(isConnected, onDisconnect));
    }, PROXY_CONFIG.HEALTH_CHECK_INTERVAL));
  };

  /**
   * Stop connection health monitoring
   */
  function stopConnectionHealthCheck(): void {
    if (!isDefined(healthCheckInterval)) {
      return;
    }
    clearInterval(get(healthCheckInterval));
    set(healthCheckInterval, undefined);
  }

  /**
   * Integrated health check logic
   */
  async function performHealthCheck(isConnected: () => boolean, onDisconnect: () => void): Promise<void> {
    if (get(isHealthCheckActive) && isConnected()) {
      try {
        const connected = await isProxyClientConnected();
        if (!connected) {
          logger.debug('Health check detected disconnection');
          onDisconnect();
          stopConnectionHealthCheck();
        }
      }
      catch (error) {
        logger.error('Bridge health check error:', error);
        onDisconnect();
        stopConnectionHealthCheck();
      }
    }
  }

  function cleanupResources(): void {
    logger.debug('Cleaning up bridge resources...');
    stopConnectionHealthCheck();
    // Only cleanup setup resources if setup is not currently in progress
    // to avoid aborting an ongoing setup process
    if (!activeResources.isSetupInProgress) {
      cleanupActiveResources();
    }
    else {
      logger.debug('Setup in progress, skipping abort of setup controller');
    }
  }

  // Wait for servers to be listening before opening webpage
  const waitForServersListening = async (
    timeoutMs: number = PROXY_CONFIG.SERVER_TIMEOUT,
    signal?: AbortSignal,
  ): Promise<void> => {
    await waitForCondition(
      async () => {
        const [httpListening, wsListening] = await Promise.all([
          isProxyHttpListening(),
          isProxyWebSocketListening(),
        ]);
        return { httpListening, wsListening };
      },
      result => result.httpListening && result.wsListening,
      {
        interval: PROXY_CONFIG.RETRY_INTERVAL,
        name: 'servers to start listening',
        signal,
        timeout: timeoutMs,
      },
    );
  };

  // Initialize wallet bridge
  async function initializeProxy(): Promise<void> {
    const walletBridge = (window as any).walletBridge;
    if (!walletBridge) {
      throw new Error('Wallet bridge not available in window object');
    }

    if (!walletBridge.isEnabled()) {
      logger.debug('Enabling wallet bridge...');
      try {
        await walletBridge.enable();
        logger.debug('Wallet bridge enabled successfully');
      }
      catch (error) {
        throw new Error(`Failed to enable wallet bridge: ${(error as Error).message}`);
      }
    }
    else {
      logger.debug('Wallet bridge already enabled');
    }
  }

  // Start bridge servers and establish connection
  const startProxyServers = async (signal?: AbortSignal): Promise<void> => {
    logger.debug('Starting bridge servers...');

    try {
      await openProxyPageInDefaultBrowser();
      logger.debug('Bridge servers startup initiated');
      await waitForServersListening(PROXY_CONFIG.SERVER_TIMEOUT, signal);
      logger.debug('Bridge servers are now listening');
      await waitForProxyConnection(PROXY_CONFIG.CONNECTION_TIMEOUT, signal);
      logger.debug('Bridge client connection established');
      await waitForProxyClientReady(PROXY_CONFIG.CONNECTION_TIMEOUT, signal);
      logger.debug('Bridge client ready for API calls');
    }
    catch (error) {
      const err = error as Error;
      logger.error('Bridge setup failed:', err);
      throw new Error(`Failed to establish bridge connection during bridge setup: ${err.message}`);
    }
  };

  // Main setup function with improved flow control and lifecycle management
  const setupProxy = async (): Promise<void> => {
    // Prevent concurrent setup operations
    if (activeResources.isSetupInProgress) {
      logger.debug('Bridge setup already in progress, skipping...');
      return;
    }

    logger.debug('Starting bridge setup process...');
    activeResources.isSetupInProgress = true;

    try {
      await initializeProxy();
      const bridgeState = await checkProxyState();

      const isFullyConnected = bridgeState.httpListening && bridgeState.wsListening && bridgeState.clientConnected;

      if (isFullyConnected) {
        const isClientReady = await isProxyClientReady();
        if (!isClientReady) {
          logger.debug('Bridge is already fully operational, opening bridge page');
          await openProxyPageInDefaultBrowser();
        }

        return;
      }

      // Step 4: Start servers if needed
      const missingServices = [];
      if (!bridgeState.httpListening)
        missingServices.push('HTTP server');
      if (!bridgeState.wsListening)
        missingServices.push('WebSocket server');
      if (!bridgeState.clientConnected)
        missingServices.push('client connection');

      logger.debug(`Bridge setup required for: ${missingServices.join(', ')}`);

      // Step 5: Set up cancellation for the entire process with resource tracking
      activeResources.setupAbortController = new AbortController();
      const totalTimeout = PROXY_CONFIG.SERVER_TIMEOUT + PROXY_CONFIG.CONNECTION_TIMEOUT;
      activeResources.setupTimeout = setTimeout(() => {
        logger.debug('Bridge setup timeout reached, aborting...');
        activeResources.setupAbortController?.abort();
      }, totalTimeout);

      try {
        await startProxyServers(activeResources.setupAbortController.signal);
        logger.debug('Bridge setup completed successfully');
      }
      finally {
        if (activeResources.setupTimeout) {
          clearTimeout(activeResources.setupTimeout);
          activeResources.setupTimeout = null;
        }
        activeResources.setupAbortController = null;
      }
    }
    finally {
      activeResources.isSetupInProgress = false;
    }
  };

  const disconnectProxy = async (): Promise<void> => {
    logger.debug('Disconnecting bridge and stopping servers...');

    cleanupResources();

    try {
      // Use the new proper server stop functionality instead of just disable
      await proxyStopServers();
      logger.debug('Bridge servers stopped successfully');
    }
    catch (error) {
      logger.error('Failed to stop bridge servers:', error);
      throw new Error(`Failed to stop bridge servers: ${(error as Error).message}`);
    }
  };

  // Cleanup on component unmount
  onBeforeUnmount(() => {
    logger.debug('Component unmounting, cleaning up bridge resources...');
    cleanupResources();
  });

  return {
    disconnectProxy,
    setupProxy,
    startConnectionHealthCheck,
    stopConnectionHealthCheck,
    waitForProxyClientReady,
    waitForProxyConnection,
  };
}
