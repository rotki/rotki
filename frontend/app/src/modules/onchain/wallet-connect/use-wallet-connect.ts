import type { Ref } from 'vue';
import { EthersAdapter } from '@reown/appkit-adapter-ethers';
import { type AppKitNetwork, arbitrum, base, bsc, gnosis, mainnet, optimism, polygon, scroll } from '@reown/appkit/networks';
import { type AppKit, createAppKit } from '@reown/appkit/vue';
import { BrowserProvider, getAddress } from 'ethers';
import { logger } from '@/utils/logging';

export const ROTKI_DAPP_METADATA = {
  description: 'Rotki Dapp',
  icons: ['https://raw.githubusercontent.com/rotki/data/refs/heads/main/assets/default_icons/website_logo.png'],
  name: 'Rotki Dapp',
  url: 'https://rotki.com',
};

export const EIP155 = 'eip155';

export const supportedNetworks: [AppKitNetwork, ...AppKitNetwork[]] = [
  mainnet,
  base,
  arbitrum,
  optimism,
  bsc,
  gnosis,
  polygon,
  scroll,
] as const;

function buildAppKit(): AppKit {
  const projectId = import.meta.env.VITE_WALLET_CONNECT_PROJECT_ID as string;

  return createAppKit({
    adapters: [new EthersAdapter()],
    allowUnsupportedChain: true,
    features: {
      analytics: true,
      email: false,
      onramp: false,
      socials: false,
      swaps: false,
    },
    metadata: ROTKI_DAPP_METADATA,
    networks: supportedNetworks,
    projectId,
    themeVariables: {
      '--w3m-z-index': 10000,
    },
  });
}

interface UseWalletConnectReturn {
  connected: Ref<boolean>;
  connectedAddress: Ref<string | undefined>;
  connectedChainId: Ref<number | undefined>;
  supportedChainIds: Ref<string[]>;
  isWalletConnect: Ref<boolean>;
  preparing: Ref<boolean>;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  getBrowserProvider: () => import('ethers').BrowserProvider;
  switchNetwork: (chainId: bigint) => Promise<void>;
  checkWalletConnection: () => Promise<void>;
}

export function useWalletConnect(): UseWalletConnectReturn {
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string | undefined>();
  const connectedChainId = ref<number | undefined>();
  const supportedChainIds = ref<string[]>([]);
  const isWalletConnect = ref<boolean>(false);
  const preparing = ref<boolean>(false);

  let appKit: AppKit | undefined;

  const getAppKit = (): AppKit => {
    if (!appKit) {
      logger.debug('Initializing AppKit');
      appKit = buildAppKit();
      setupAppKitListener();
    }
    return appKit;
  };

  const updateApprovedChainIds = (): void => {
    const appKitInstance = getAppKit();

    // @ts-expect-error accessing protected method to get approved chain IDs
    const data = appKitInstance.getApprovedCaipNetworksData();
    if (data) {
      const approvedCaipNetworkIds = data.approvedCaipNetworkIds;
      set(supportedChainIds, approvedCaipNetworkIds);
    }
  };

  function setupAppKitListener(): void {
    if (!appKit)
      return;

    appKit.subscribeAccount((account) => {
      if (!appKit)
        return;

      set(connected, account.isConnected);
      set(connectedAddress, account.isConnected && account.address ? getAddress(account.address) : undefined);

      if (account.isConnected) {
        const provider: any = appKit.getProvider(EIP155);
        set(isWalletConnect, provider && 'isWalletConnect' in provider && provider.isWalletConnect);

        const chainId = appKit.getCaipNetworkId();
        if (chainId) {
          set(connectedChainId, chainId);
        }
      }

      updateApprovedChainIds();
    });

    appKit.subscribeNetwork((newState) => {
      set(connectedChainId, newState.chainId);
    });
  }

  const connect = async (): Promise<void> => {
    const appKitInstance = getAppKit();
    await appKitInstance.open();
  };

  const disconnect = async (): Promise<void> => {
    if (appKit) {
      await appKit.disconnect();
    }

    // Reset state
    set(connected, false);
    set(connectedAddress, undefined);
    set(connectedChainId, undefined);
    set(supportedChainIds, []);
    set(isWalletConnect, false);
    set(preparing, false);
    appKit = undefined;
  };

  const getBrowserProvider = (): BrowserProvider => {
    const appKitInstance = getAppKit();
    const walletProvider = appKitInstance.getProvider(EIP155);
    return new BrowserProvider(walletProvider as any);
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    const appKitInstance = getAppKit();
    const network = supportedNetworks.find(item => BigInt(item.id) === chainId);
    if (network) {
      await appKitInstance.switchNetwork(network);
    }
  };

  const checkWalletConnection = async (): Promise<void> => {
    const appKitInstance = getAppKit();
    const universalProvider = await appKitInstance.getUniversalProvider();

    if (!universalProvider?.isWalletConnect)
      return;

    try {
      const session = universalProvider.session;
      if (session?.topic) {
        set(preparing, true);
        const pingPromise = universalProvider.client.ping({ topic: session.topic });
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Ping timeout after 5s')), 5000);
        });

        await Promise.race([pingPromise, timeoutPromise]);
      }
    }
    catch {
      throw new Error('It seems that your wallet is inactive. If you are using browser wallet bridge, make sure the page is open.');
    }
    finally {
      set(preparing, false);
    }
  };

  return {
    checkWalletConnection,
    connect,
    connected,
    connectedAddress,
    connectedChainId,
    disconnect,
    getBrowserProvider,
    isWalletConnect,
    preparing,
    supportedChainIds,
    switchNetwork,
  };
}
