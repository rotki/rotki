import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import { logicOr } from '@vueuse/math';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type Ref } from 'vue';
import { useUnifiedProviders } from '@/modules/wallet/providers/use-unified-providers';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

export const GNOSIS_CHAIN_ID = 100;

interface UseGnosisPayWalletStatusReturn {
  availableProviders: Readonly<Ref<EnhancedProviderDetail[]>>;
  /** True while browser wallet providers are being detected. */
  detectingProviders: Readonly<Ref<boolean>>;
  /** True while a connection is being prepared or the providers are still being detected. */
  isConnecting: ComputedRef<boolean>;
  isDisconnecting: Ref<boolean>;
  isOnGnosisChain: ComputedRef<boolean>;
  /** True for a WalletConnect session, false for an injected wallet. */
  isWalletConnect: ComputedRef<boolean>;
  showProviderSelection: Ref<boolean>;
}

/**
 * Composable for the connected wallet's state as the Gnosis Pay sign-in shows it
 */
export function useGnosisPayWalletStatus(): UseGnosisPayWalletStatusReturn {
  const walletStore = useWalletStore();
  const { connectedChainId, isDisconnecting, isWalletConnect, preparing } = storeToRefs(walletStore);

  const { availableProviders, isDetecting: detectingProviders, showProviderSelection } = useUnifiedProviders();

  const isOnGnosisChain = computed<boolean>(() => get(connectedChainId) === GNOSIS_CHAIN_ID);
  const isConnecting = logicOr(preparing, detectingProviders);

  return {
    availableProviders,
    detectingProviders,
    isConnecting,
    isDisconnecting,
    isOnGnosisChain,
    isWalletConnect,
    showProviderSelection,
  };
}
