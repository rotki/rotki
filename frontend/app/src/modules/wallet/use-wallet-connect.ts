import type UniversalProvider from '@walletconnect/universal-provider';
import type { Ref } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { EIP155, EIP155_EVENTS, EIP155_METHODS } from './constants';
import { type Chain, createViemWalletClient, getAddress, type ViemWalletClient } from './viem-client';

type WcSession = NonNullable<UniversalProvider['session']>;

const ROTKI_DAPP_METADATA = {
  description: 'Rotki Dapp',
  icons: ['https://raw.githubusercontent.com/rotki/data/refs/heads/main/assets/default_icons/website_logo.png'],
  name: 'Rotki Dapp',
  url: 'https://rotki.com',
};

// viem chain objects are only needed once WalletConnect actually connects, so
// the `chains-viem` module (and the viem chain definitions it pulls) is loaded
// lazily and memoised, keeping viem's chain data out of the initial bundle.
let walletNetworksPromise: Promise<readonly Chain[]> | undefined;

async function loadWalletNetworks(): Promise<readonly Chain[]> {
  if (!walletNetworksPromise)
    walletNetworksPromise = import('./chains-viem').then(mod => mod.SUPPORTED_WALLET_NETWORKS);

  return walletNetworksPromise;
}

// Module-level singletons: the provider and the connection state are shared by
// every caller of `useWalletConnect()` (the store, gnosis-pay, the QR dialog),
// mirroring how the previous AppKit instance was effectively global.
let providerInstance: UniversalProvider | undefined;
let providerPromise: Promise<UniversalProvider> | undefined;
let listenersBound = false;
let connectAborted = false;

const connected = ref<boolean>(false);
const connectedAddress = ref<string>();
const connectedChainId = ref<number>();
const supportedChainIds = ref<string[]>([]);
const isWalletConnect = ref<boolean>(false);
const preparing = ref<boolean>(false);

// QR connect modal state, consumed by `WalletConnectQrDialog.vue`.
const connectUri = ref<string>();
const showConnectModal = ref<boolean>(false);

interface UseWalletConnectReturn {
  connected: Ref<boolean>;
  connectedAddress: Ref<string | undefined>;
  connectedChainId: Ref<number | undefined>;
  supportedChainIds: Ref<string[]>;
  isWalletConnect: Ref<boolean>;
  preparing: Ref<boolean>;
  connectUri: Ref<string | undefined>;
  showConnectModal: Ref<boolean>;
  connect: () => Promise<void>;
  cancelConnect: () => void;
  disconnect: () => Promise<void>;
  getWalletClient: () => ViemWalletClient;
  switchNetwork: (chainId: bigint) => Promise<void>;
  checkWalletConnection: () => Promise<void>;
}

function parseChainId(chain: string): number {
  const raw = chain.includes(':') ? chain.split(':').pop() ?? chain : chain;
  return raw.startsWith('0x') ? parseInt(raw, 16) : Number(raw);
}

function resetState(): void {
  set(connected, false);
  set(connectedAddress, undefined);
  set(connectedChainId, undefined);
  set(supportedChainIds, []);
  set(isWalletConnect, false);
  set(preparing, false);
}

function syncSession(session: WcSession): void {
  const namespace = session.namespaces[EIP155];
  const accounts = namespace?.accounts ?? [];

  set(connected, accounts.length > 0);

  if (accounts.length > 0) {
    // CAIP-10 account id, e.g. `eip155:1:0xabc...`
    const [first] = accounts;
    const [, chainId, address] = first.split(':');
    if (address)
      set(connectedAddress, getAddress(address));
    if (chainId)
      set(connectedChainId, Number(chainId));
  }

  set(isWalletConnect, providerInstance?.isWalletConnect ?? true);
  set(supportedChainIds, namespace?.chains ?? accounts.map(account => account.split(':').slice(0, 2).join(':')));
}

function onAccountsChanged(accounts: string[]): void {
  if (!accounts || accounts.length === 0) {
    resetState();
    return;
  }
  const address = accounts[0].includes(':') ? accounts[0].split(':').pop() : accounts[0];
  if (address) {
    set(connectedAddress, getAddress(address));
    set(connected, true);
  }
}

function onChainChanged(chain: string): void {
  set(connectedChainId, parseChainId(chain));
}

function onDisplayUri(uri: string): void {
  set(connectUri, uri);
  set(showConnectModal, true);
}

function bindListeners(provider: UniversalProvider): void {
  if (listenersBound)
    return;

  provider.on('connect', () => {
    if (provider.session)
      syncSession(provider.session);
  });
  provider.on('session_update', () => {
    if (provider.session)
      syncSession(provider.session);
  });
  provider.on('accountsChanged', onAccountsChanged);
  provider.on('chainChanged', onChainChanged);
  provider.on('disconnect', resetState);
  provider.on('session_delete', resetState);
  listenersBound = true;
}

async function getProvider(): Promise<UniversalProvider> {
  if (providerInstance)
    return providerInstance;

  if (!providerPromise) {
    logger.debug('Initializing WalletConnect Universal Provider');
    providerPromise = import('@walletconnect/universal-provider').then(async mod =>
      mod.UniversalProvider.init({
        metadata: ROTKI_DAPP_METADATA,
        projectId: import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID,
      }),
    );
  }

  const provider = await providerPromise;
  bindListeners(provider);
  providerInstance = provider;

  // Restore any session rehydrated from storage during init().
  if (provider.session)
    syncSession(provider.session);

  return provider;
}

function closeModal(): void {
  set(showConnectModal, false);
  set(connectUri, undefined);
}

export function useWalletConnect(): UseWalletConnectReturn {
  const connect = async (): Promise<void> => {
    const provider = await getProvider();

    if (provider.session) {
      syncSession(provider.session);
      return;
    }

    connectAborted = false;
    set(preparing, true);
    provider.on('display_uri', onDisplayUri);

    try {
      const networks = await loadWalletNetworks();
      const chains = networks.map(network => `${EIP155}:${network.id}`);
      const rpcMap: Record<string, string> = {};
      for (const network of networks) {
        const url = network.rpcUrls.default.http[0];
        if (url)
          rpcMap[`${EIP155}:${network.id}`] = url;
      }

      await provider.connect({
        optionalNamespaces: {
          [EIP155]: {
            chains,
            events: [...EIP155_EVENTS],
            methods: [...EIP155_METHODS],
            rpcMap,
          },
        },
      });

      if (provider.session)
        syncSession(provider.session);
    }
    catch (error) {
      // User closed the QR dialog: pairing was aborted on purpose, stay quiet.
      if (connectAborted) {
        logger.debug('WalletConnect pairing aborted by user');
        return;
      }
      throw error;
    }
    finally {
      provider.removeListener('display_uri', onDisplayUri);
      closeModal();
      set(preparing, false);
    }
  };

  const cancelConnect = (): void => {
    connectAborted = true;
    if (providerInstance) {
      try {
        providerInstance.abortPairingAttempt();
      }
      catch (error) {
        logger.debug('Failed to abort WalletConnect pairing', error);
      }
    }
    closeModal();
  };

  const disconnect = async (): Promise<void> => {
    if (providerInstance?.session)
      await providerInstance.disconnect();

    resetState();
  };

  const getWalletClient = (): ViemWalletClient => {
    if (!providerInstance)
      throw new Error('WalletConnect provider not available');

    return createViemWalletClient(providerInstance);
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    if (!providerInstance)
      return;

    await providerInstance.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: `0x${chainId.toString(16)}` }],
    });

    const { getWalletNetwork } = await import('./chains-viem');
    const network = getWalletNetwork(chainId);
    providerInstance.setDefaultChain(`${EIP155}:${chainId}`, network?.rpcUrls.default.http[0]);
  };

  const checkWalletConnection = async (): Promise<void> => {
    const provider = providerInstance;
    if (!provider?.session || !provider.isWalletConnect)
      return;

    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    try {
      set(preparing, true);
      const pingPromise = provider.client.ping({ topic: provider.session.topic });
      const timeoutPromise = new Promise((_, reject) => {
        timeoutId = setTimeout(() => reject(new Error('Ping timeout after 5s')), 5000);
      });

      await Promise.race([pingPromise, timeoutPromise]);
    }
    catch {
      throw new Error('It seems that your wallet is inactive. If you are using browser wallet bridge, make sure the page is open.');
    }
    finally {
      if (timeoutId)
        clearTimeout(timeoutId);
      set(preparing, false);
    }
  };

  return {
    cancelConnect,
    checkWalletConnection,
    connect,
    connected,
    connectedAddress,
    connectedChainId,
    connectUri,
    disconnect,
    getWalletClient,
    isWalletConnect,
    preparing,
    showConnectModal,
    supportedChainIds,
    switchNetwork,
  };
}
