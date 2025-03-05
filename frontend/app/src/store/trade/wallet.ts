import { WagmiAdapter } from '@reown/appkit-adapter-wagmi';
import { type AppKitNetwork, arbitrum, base, bsc, gnosis, mainnet, optimism, polygon, scroll } from '@reown/appkit/networks';
import { type AppKit, createAppKit } from '@reown/appkit/vue';
import { assert, Blockchain } from '@rotki/common';

export const ROTKI_DAPP_METADATA = {
  description: 'Rotki Dapp',
  icons: ['https://raw.githubusercontent.com/rotki/data/refs/heads/main/assets/default_icons/website_logo.png'],
  name: 'Rotki Dapp',
  url: 'https://rotki.com',
};

export const EIP155 = 'eip155';

const WC_PROJECT_ID = 'eca1bd3842e084bfc8ef309b6eb584db';

export type StepType = 'pending' | 'failure' | 'success';

export type IdleStep = 'idle';

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

export const tradableChains = [
  Blockchain.ETH,
  Blockchain.BASE,
  Blockchain.ARBITRUM_ONE,
  Blockchain.OPTIMISM,
  Blockchain.BSC,
  Blockchain.GNOSIS,
  Blockchain.POLYGON_POS,
  Blockchain.SCROLL,
];

export function getChainIdFromNamespace(namespace: string): number {
  return Number(namespace.replace(`${EIP155}:`, ''));
}

function buildAppKit(): AppKit {
  const wagmiAdapter = new WagmiAdapter({
    networks: supportedNetworks,
    projectId: WC_PROJECT_ID,
    ssr: false,
  });

  return createAppKit({
    adapters: [wagmiAdapter],
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
    projectId: WC_PROJECT_ID,
  });
}

export const useWalletStore = defineStore('wallet', () => {
  const connected = ref<boolean>(false);
  const connectedAddress = ref<string>();
  const state = ref<StepType | IdleStep>('idle');
  const connectedChainId = ref<number>();
  const supportedChainIds = ref<string[]>([]);
  const appKit = ref<AppKit>();

  const setupAppKitListener = (): void => {
    const kit = get(appKit);
    assert(kit);

    kit.subscribeAccount((account) => {
      set(state, 'idle');
      set(connected, account.isConnected);
      set(connectedAddress, account.isConnected ? account.address : undefined);
      set(supportedChainIds, kit.getApprovedCaipNetworkIds());

      const chainId = kit.getCaipNetworkId();
      if (account.isConnected && chainId) {
        set(connectedChainId, chainId);
      }
    });
  };

  watchImmediate(appKit, (kit) => {
    if (!kit) {
      set(appKit, buildAppKit());
      setupAppKitListener();
    }
  });

  const open = async (): Promise<void> => {
    const kit = get(appKit);
    assert(kit);
    await kit.open();
  };

  const resetState = (): void => {
    set(connected, false);
    set(state, 'idle');
    set(connectedAddress, undefined);
    set(supportedChainIds, []);
  };

  const disconnect = async (): Promise<void> => {
    const kit = get(appKit);
    assert(kit);
    await kit.disconnect();
    resetState();
  };

  const switchNetwork = async (chainId: bigint): Promise<void> => {
    const kit = get(appKit);
    assert(kit);
    const network = supportedNetworks.find(item => BigInt(item.id) === chainId);
    if (network) {
      await kit.switchNetwork(network);
    }
  };

  return {
    connected,
    connectedAddress,
    connectedChainId,
    disconnect,
    open,
    supportedChainIds,
    switchNetwork,
  };
});
