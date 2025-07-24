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
import { setupWalletBridgeProvider } from './use-wallet-bridge-provider';

const BRIDGE_CONFIG = {
  BRIDGE_PAGE_DELAY: 250,
  CONNECTION_TIMEOUT: 30000,
  HEALTH_CHECK_INTERVAL: 5000,
  RETRY_INTERVAL: 500,
  SERVER_TIMEOUT: 30000,
} as const;

interface UseBridgedWalletReturn {
  setupBridge: () => Promise<void>;
  waitForBridgeConnection: (timeoutMs?: number, signal?: AbortSignal) => Promise<void>;
  waitForBridgeClientReady: (timeoutMs?: number, signal?: AbortSignal) => Promise<void>;
  startConnectionHealthCheck: (isConnected: () => boolean, onDisconnect: () => void) => void;
  stopConnectionHealthCheck: () => void;
  disconnectBridge: () => Promise<void>;
}

export function useBridgedWallet(): UseBridgedWalletReturn {
  const { openWalletBridge, walletBridgeClientReady, walletBridgeConnect, walletBridgeHttpListening, walletBridgeWebSocketListening } = useWalletBridge();

  // Track active resources for cleanup
  const { cleanupResources: cleanupActiveResources, resources: activeResources } = createResourceManager();

  // Create health check composable
  const healthCheck = useHealthCheck(
    async () => walletBridgeConnect(),
    {
      interval: BRIDGE_CONFIG.HEALTH_CHECK_INTERVAL,
      onError: (error: Error) => {
        logger.error('Bridge health check error:', error);
      },
    },
  );

  // Check current bridge state
  const checkBridgeState = async (): Promise<{
    httpListening: boolean;
    wsListening: boolean;
    clientConnected: boolean;
  }> => {
    // Check servers and connection in parallel for faster state assessment
    const [httpListening, wsListening, clientConnected] = await Promise.all([
      walletBridgeHttpListening(),
      walletBridgeWebSocketListening(),
      walletBridgeConnect(),
    ]);

    const state = { clientConnected, httpListening, wsListening };
    logger.debug('Bridge state check:', {
      client: state.clientConnected ? 'connected' : 'disconnected',
      httpServer: state.httpListening ? 'listening' : 'not listening',
      wsServer: state.wsListening ? 'listening' : 'not listening',
    });

    return state;
  };

  const waitForBridgeConnection = async (
    timeoutMs: number = BRIDGE_CONFIG.CONNECTION_TIMEOUT,
    signal?: AbortSignal,
  ): Promise<void> => {
    await waitForConditionBridge(
      async () => walletBridgeConnect(),
      connected => connected,
      {
        initialDelay: BRIDGE_CONFIG.BRIDGE_PAGE_DELAY,
        interval: BRIDGE_CONFIG.RETRY_INTERVAL,
        name: 'bridge connection',
        signal,
        timeout: timeoutMs,
      },
    );
  };

  const waitForBridgeClientReady = async (
    timeoutMs: number = BRIDGE_CONFIG.CONNECTION_TIMEOUT,
    signal?: AbortSignal,
  ): Promise<void> => {
    await waitForConditionBridge(
      async () => walletBridgeClientReady(),
      ready => ready,
      {
        initialDelay: BRIDGE_CONFIG.BRIDGE_PAGE_DELAY,
        interval: BRIDGE_CONFIG.RETRY_INTERVAL,
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

  async function waitForConditionBridge<T>(checkFn: () => Promise<T>, condition: (result: T) => boolean, options: {
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
    timeoutMs: number = BRIDGE_CONFIG.SERVER_TIMEOUT,
    signal?: AbortSignal,
  ): Promise<void> => {
    await waitForConditionBridge(
      async () => {
        const [httpListening, wsListening] = await Promise.all([
          walletBridgeHttpListening(),
          walletBridgeWebSocketListening(),
        ]);
        return { httpListening, wsListening };
      },
      result => result.httpListening && result.wsListening,
      {
        interval: BRIDGE_CONFIG.RETRY_INTERVAL,
        name: 'servers to start listening',
        signal,
        timeout: timeoutMs,
      },
    );
  };

  // Initialize wallet bridge
  async function initializeWalletBridge(): Promise<void> {
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
  const startBridgeServers = async (signal?: AbortSignal): Promise<void> => {
    logger.debug('Starting bridge servers...');

    try {
      // Step 1: Start the bridge servers
      await openWalletBridge();
      logger.debug('Bridge servers startup initiated');

      // Step 2: Wait for both servers to be ready (parallel check)
      await waitForServersListening(BRIDGE_CONFIG.SERVER_TIMEOUT, signal);
      logger.debug('Bridge servers are now listening');

      // Step 3: Establish client connection
      await waitForBridgeConnection(BRIDGE_CONFIG.CONNECTION_TIMEOUT, signal);
      logger.debug('Bridge client connection established');

      // Step 4: Wait for client to be ready for API calls
      await waitForBridgeClientReady(BRIDGE_CONFIG.CONNECTION_TIMEOUT, signal);
      logger.debug('Bridge client ready for API calls');
    }
    catch (error) {
      if (error instanceof BridgeTimeoutError) {
        logger.error(`Bridge setup timed out: ${error.message}`);
        throw error;
      }
      if (error instanceof BridgeError && error.code === 'ABORTED') {
        logger.debug('Bridge setup was cancelled');
        throw new BridgeTimeoutError('bridge setup process', BRIDGE_CONFIG.SERVER_TIMEOUT + BRIDGE_CONFIG.CONNECTION_TIMEOUT, error);
      }
      logger.error('Bridge setup failed:', error);
      throw new BridgeConnectionError('bridge setup', error as Error);
    }
  };

  // Main setup function with improved flow control and lifecycle management
  const setupBridge = async (): Promise<void> => {
    // Prevent concurrent setup operations
    if (activeResources.isSetupInProgress) {
      logger.debug('Bridge setup already in progress, skipping...');
      return;
    }

    logger.debug('Starting bridge setup process...');
    activeResources.isSetupInProgress = true;

    try {
      // Step 1: Set up the wallet bridge provider in renderer context
      setupWalletBridgeProvider();

      // Step 2: Initialize the wallet bridge
      await initializeWalletBridge();

      // Step 2: Check current state
      const bridgeState = await checkBridgeState();

      // Step 3: Determine if setup is needed
      const isFullyConnected = bridgeState.httpListening && bridgeState.wsListening && bridgeState.clientConnected;

      if (isFullyConnected) {
        const isClientReady = await walletBridgeClientReady();
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
      const totalTimeout = BRIDGE_CONFIG.SERVER_TIMEOUT + BRIDGE_CONFIG.CONNECTION_TIMEOUT;
      activeResources.setupTimeout = setTimeout(() => {
        logger.debug('Bridge setup timeout reached, aborting...');
        activeResources.setupAbortController?.abort();
      }, totalTimeout);

      try {
        await startBridgeServers(activeResources.setupAbortController.signal);
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

  const disconnectBridge = async (): Promise<void> => {
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
    disconnectBridge,
    setupBridge,
    startConnectionHealthCheck,
    stopConnectionHealthCheck,
    waitForBridgeClientReady,
    waitForBridgeConnection,
  };
}
