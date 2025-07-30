import { useWalletBridge } from '@/composables/wallet-bridge';
import { useHealthCheck } from '@/modules/onchain/wallet-bridge/use-health-check';
import { AsyncUtilityError, TimeoutError, waitForCondition } from '@/utils/async-utilities';
import { logger } from '@/utils/logging';
import {
  BridgeConnectionError,
  BridgeError,
  BridgeInitializationError,
  BridgeTimeoutError,
} from './bridge-errors';
import { createResourceManager } from './resource-management';

const PROXY_CONFIG = {
  BRIDGE_PAGE_DELAY: 250,
  CONNECTION_TIMEOUT: 30000,
  HEALTH_CHECK_INTERVAL: 5000,
  RETRY_INTERVAL: 500,
  SERVER_TIMEOUT: 30000,
} as const;

interface UseWalletProxyReturn {
  setupProxy: () => Promise<void>;
  waitForProxyConnection: (timeoutMs?: number, signal?: AbortSignal) => Promise<void>;
  waitForProxyClientReady: (timeoutMs?: number, signal?: AbortSignal) => Promise<void>;
  startConnectionHealthCheck: (isConnected: () => boolean, onDisconnect: () => void) => void;
  stopConnectionHealthCheck: () => void;
  disconnectProxy: () => Promise<void>;
}

export function useWalletProxy(): UseWalletProxyReturn {
  const { openWalletBridge, proxyClientReady, proxyConnect, proxyHttpListening, proxyWebSocketListening } = useWalletBridge();

  // Track active resources for cleanup
  const { cleanupResources: cleanupActiveResources, resources: activeResources } = createResourceManager();

  // Create health check composable
  const healthCheck = useHealthCheck(
    async () => proxyConnect(),
    {
      interval: PROXY_CONFIG.HEALTH_CHECK_INTERVAL,
      onError: (error: Error) => {
        logger.error('Bridge health check error:', error);
      },
    },
  );

  // Check current bridge state
  const checkProxyState = async (): Promise<{
    httpListening: boolean;
    wsListening: boolean;
    clientConnected: boolean;
  }> => {
    // Check servers and connection in parallel for faster state assessment
    const [httpListening, wsListening, clientConnected] = await Promise.all([
      proxyHttpListening(),
      proxyWebSocketListening(),
      proxyConnect(),
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
    await waitForProxyCondition(
      async () => proxyConnect(),
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
    await waitForProxyCondition(
      async () => proxyClientReady(),
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

  function cleanupResources(): void {
    logger.debug('Cleaning up bridge resources...');
    healthCheck.stop();
    // Only cleanup setup resources if setup is not currently in progress
    // to avoid aborting an ongoing setup process
    if (!activeResources.isSetupInProgress) {
      cleanupActiveResources();
    }
    else {
      logger.debug('Setup in progress, skipping abort of setup controller');
    }
  }

  async function waitForProxyCondition<T>(checkFn: () => Promise<T>, condition: (result: T) => boolean, options: {
    timeout?: number;
    interval?: number;
    initialDelay?: number;
    name: string;
    signal?: AbortSignal;
  }): Promise<T> {
    try {
      return await waitForCondition(checkFn, condition, options);
    }
    catch (error) {
      // Translate async utility errors to bridge errors
      if (error instanceof TimeoutError) {
        throw new BridgeTimeoutError(options.name, options.timeout ?? 30000, error);
      }
      if (error instanceof AsyncUtilityError && error.code === 'ABORTED') {
        throw new BridgeError(`Operation ${options.name} was aborted`, 'ABORTED', error);
      }

      throw error;
    }
  }

  // Wait for servers to be listening before opening webpage
  const waitForServersListening = async (
    timeoutMs: number = PROXY_CONFIG.SERVER_TIMEOUT,
    signal?: AbortSignal,
  ): Promise<void> => {
    await waitForProxyCondition(
      async () => {
        const [httpListening, wsListening] = await Promise.all([
          proxyHttpListening(),
          proxyWebSocketListening(),
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
      throw new BridgeInitializationError('Wallet bridge not available in window object');
    }

    if (!walletBridge.isEnabled()) {
      logger.debug('Enabling wallet bridge...');
      try {
        await walletBridge.enable();
        logger.debug('Wallet bridge enabled successfully');
      }
      catch (error) {
        throw new BridgeInitializationError('Failed to enable wallet bridge', error as Error);
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
      // Step 1: Start the bridge servers
      await openWalletBridge();
      logger.debug('Bridge servers startup initiated');

      // Step 2: Wait for both servers to be ready (parallel check)
      await waitForServersListening(PROXY_CONFIG.SERVER_TIMEOUT, signal);
      logger.debug('Bridge servers are now listening');

      // Step 3: Establish client connection
      await waitForProxyConnection(PROXY_CONFIG.CONNECTION_TIMEOUT, signal);
      logger.debug('Bridge client connection established');

      // Step 4: Wait for client to be ready for API calls
      await waitForProxyClientReady(PROXY_CONFIG.CONNECTION_TIMEOUT, signal);
      logger.debug('Bridge client ready for API calls');
    }
    catch (error) {
      if (error instanceof BridgeTimeoutError) {
        logger.error(`Bridge setup timed out: ${error.message}`);
        throw error;
      }
      if (error instanceof BridgeError && error.code === 'ABORTED') {
        logger.debug('Bridge setup was cancelled');
        throw new BridgeTimeoutError('bridge setup process', PROXY_CONFIG.SERVER_TIMEOUT + PROXY_CONFIG.CONNECTION_TIMEOUT, error);
      }
      logger.error('Bridge setup failed:', error);
      throw new BridgeConnectionError('bridge setup', error as Error);
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
      // Step 1: Initialize the wallet bridge
      await initializeProxy();

      // Step 2: Check current state
      const bridgeState = await checkProxyState();

      // Step 3: Determine if setup is needed
      const isFullyConnected = bridgeState.httpListening && bridgeState.wsListening && bridgeState.clientConnected;

      if (isFullyConnected) {
        const isClientReady = await proxyClientReady();
        if (!isClientReady) {
          logger.debug('Bridge is already fully operational, opening bridge page');
          await openWalletBridge();
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

  const startConnectionHealthCheck = (
    isConnected: () => boolean,
    onDisconnect: () => void,
  ): void => {
    healthCheck.start(isConnected, onDisconnect);
  };

  const stopConnectionHealthCheck = (): void => {
    healthCheck.stop();
  };

  const disconnectProxy = async (): Promise<void> => {
    logger.debug('Disconnecting bridge...');

    cleanupResources();

    const walletBridge = window.walletBridge;
    if (walletBridge) {
      try {
        await walletBridge.disable();
        logger.debug('Bridge disconnected successfully');
      }
      catch (error) {
        logger.error('Failed to disconnect bridge:', error);
        throw new BridgeError('Failed to disconnect bridge', 'BRIDGE_DISCONNECT_ERROR', error as Error);
      }
    }
    else {
      logger.debug('No wallet bridge to disconnect');
    }
  };

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
