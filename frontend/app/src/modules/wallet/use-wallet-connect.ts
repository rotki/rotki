import type UniversalProvider from '@walletconnect/universal-provider';
import type { Ref } from 'vue';
import { withTimeout } from '@/modules/core/common/async/async-utilities';
import { logger } from '@/modules/core/common/logging/logging';
import { EIP155, EIP155_EVENTS, EIP155_METHODS, WALLET_ERRORS } from './constants';
import { type Chain, createViemWalletClient, getAddress, type ViemWalletClient } from './viem-client';

type WcSession = NonNullable<UniversalProvider['session']>;

const ROTKI_DAPP_METADATA = {
  description: 'Rotki Dapp',
  icons: ['https://raw.githubusercontent.com/rotki/data/refs/heads/main/assets/default_icons/website_logo.png'],
  name: 'Rotki Dapp',
  url: 'https://rotki.com',
};

/**
 * Memoises the lazy `chains-viem` import, whose viem chain definitions are only needed once
 * WalletConnect actually connects, and so are kept out of the initial bundle.
 */
let walletNetworksPromise: Promise<readonly Chain[]> | undefined;

async function loadWalletNetworks(): Promise<readonly Chain[]> {
  walletNetworksPromise ??= import('./chains-viem').then(mod => mod.SUPPORTED_WALLET_NETWORKS);

  return walletNetworksPromise;
}

/**
 * The `rpcMap` a session is opened with. It is a hint the wallet may ignore, and
 * `chains-viem` only knows the chains viem ships a definition for, so a chain
 * with no entry is simply requested without a URL rather than withheld.
 */
async function getRpcMap(chainIds: number[]): Promise<Record<string, string>> {
  const networks = await loadWalletNetworks();
  const rpcMap: Record<string, string> = {};
  for (const chainId of chainIds) {
    const url = networks.find(network => network.id === chainId)?.rpcUrls.default.http[0];
    if (url)
      rpcMap[`${EIP155}:${chainId}`] = url;
  }
  return rpcMap;
}

const PING_TIMEOUT = 5000;

/**
 * Module-level singletons: the provider and the connection state are shared by every caller of
 * {@link useWalletConnect}, which is the store, gnosis-pay and the QR dialog alike.
 */
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
  connect: (chainIds: number[]) => Promise<void>;
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
  /**
   * @param chainIds - the EIP-155 chain ids to request in the session namespace. They come from the
   * caller rather than from `chains-viem`, so the session covers every chain rotki supports and not
   * only the ones viem is imported for.
   */
  const connect = async (chainIds: number[]): Promise<void> => {
    if (chainIds.length === 0)
      throw new Error(WALLET_ERRORS.NO_SUPPORTED_CHAINS);

    const provider = await getProvider();

    if (provider.session) {
      syncSession(provider.session);
      return;
    }

    connectAborted = false;
    set(preparing, true);
    provider.on('display_uri', onDisplayUri);

    try {
      const rpcMap = await getRpcMap(chainIds);

      await provider.connect({
        optionalNamespaces: {
          [EIP155]: {
            chains: chainIds.map(chainId => `${EIP155}:${chainId}`),
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

    try {
      set(preparing, true);
      await withTimeout(provider.client.ping({ topic: provider.session.topic }), PING_TIMEOUT, 'wallet ping');
    }
    catch {
      throw new Error('It seems that your wallet is inactive. If you are using browser wallet bridge, make sure the page is open.');
    }
    finally {
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
