import type { ComputedRef, Ref } from 'vue';
import type { EnhancedProviderDetail } from '@/modules/onchain/wallet-providers/provider-detection';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';
import { useProviderSelection } from '@/modules/onchain/wallet-providers/use-provider-selection';
import { logger } from '@/utils/logging';
import { type GnosisPayAdminsMapping, GnosisPayError, type GnosisPayErrorContext } from './types';
import { useGnosisPaySiweApi } from './use-gnosis-pay-api';

interface UseGnosisPayWalletOptions {
  checkingRegisteredAccounts: Ref<boolean>;
  clearError: () => void;
  clearValidation: () => void;
  controlledSafeAddresses: Ref<string[]>;
  gnosisPayAdminsMapping: Ref<GnosisPayAdminsMapping>;
  hasRegisteredAccounts: Ref<boolean>;
  isAddressValid: Ref<boolean>;
  setError: (type: GnosisPayError, context?: GnosisPayErrorContext) => void;
  validatingAddress: Ref<boolean>;
}

interface UseGnosisPayWalletReturn {
  checkRegisteredAccounts: () => Promise<void>;
  connect: () => Promise<void>;
  connectedAddress: Ref<string | undefined>;
  disconnect: () => Promise<void>;
  handleProviderSelection: (provider: EnhancedProviderDetail) => Promise<void>;
  isWalletConnected: ComputedRef<boolean>;
  validateAddress: () => Promise<void>;
}

/**
 * Composable for managing wallet connection and address validation
 */
export function useGnosisPayWallet(options: UseGnosisPayWalletOptions): UseGnosisPayWalletReturn {
  const {
    checkingRegisteredAccounts,
    clearError,
    clearValidation,
    controlledSafeAddresses,
    gnosisPayAdminsMapping,
    hasRegisteredAccounts,
    isAddressValid,
    setError,
    validatingAddress,
  } = options;

  const { fetchGnosisPayAdmins } = useGnosisPaySiweApi();
  const walletStore = useWalletStore();
  const { connected, connectedAddress } = storeToRefs(walletStore);
  const { connect: connectWallet, disconnect: disconnectWallet } = walletStore;

  const isWalletConnected = computed<boolean>(() => get(connected) && !!get(connectedAddress));

  const { handleProviderSelection: handleProviderSelectionBase } = useProviderSelection();

  async function checkRegisteredAccounts(): Promise<void> {
    try {
      clearError();
      set(checkingRegisteredAccounts, true);
      set(hasRegisteredAccounts, false);

      const admins = await fetchGnosisPayAdmins();

      // Check if there are any registered Gnosis Pay safe accounts
      if (Object.keys(admins).length === 0) {
        setError(GnosisPayError.NO_REGISTERED_ACCOUNTS);
        return;
      }

      set(hasRegisteredAccounts, true);
      set(gnosisPayAdminsMapping, admins);
    }
    catch (error: any) {
      set(hasRegisteredAccounts, false);
      logger.error('Failed to check registered accounts:', error);
      setError(GnosisPayError.OTHER, { message: error.message || error.toString() });
    }
    finally {
      set(checkingRegisteredAccounts, false);
    }
  }

  async function handleProviderSelection(provider: EnhancedProviderDetail): Promise<void> {
    await handleProviderSelectionBase(provider, (message) => {
      setError(GnosisPayError.CONNECTION_FAILED, { message });
    });
  }

  async function validateAddress(): Promise<void> {
    try {
      clearError();
      set(validatingAddress, true);
      clearValidation();

      const address = get(connectedAddress);
      if (!address) {
        setError(GnosisPayError.NO_WALLET_CONNECTED);
        return;
      }

      const adminsMapping = get(gnosisPayAdminsMapping);
      const addressLower = address.toLowerCase();

      // Find all safe addresses this admin address controls
      const foundSafeAddresses = Object.entries(adminsMapping)
        .filter(([, adminAddresses]) =>
          adminAddresses.some(adminAddr => adminAddr.toLowerCase() === addressLower))
        .map(([safeAddress]) => safeAddress);

      if (foundSafeAddresses.length === 0) {
        setError(GnosisPayError.INVALID_ADDRESS, { adminsMapping });
        return;
      }

      set(isAddressValid, true);
      set(controlledSafeAddresses, foundSafeAddresses);
    }
    catch (error: any) {
      clearValidation();
      logger.error('Address validation failed:', error);
      setError(GnosisPayError.OTHER, { message: error.message || error.toString() });
    }
    finally {
      set(validatingAddress, false);
    }
  }

  async function connect(): Promise<void> {
    try {
      clearError();
      clearValidation();
      await connectWallet();
      // Address validation will be triggered by the watcher when connectedAddress changes
    }
    catch (error: any) {
      logger.error(error);
      setError(GnosisPayError.CONNECTION_FAILED, { message: error.message });
    }
  }

  async function disconnect(): Promise<void> {
    try {
      clearError();
      clearValidation();
      await disconnectWallet();
    }
    catch (error: any) {
      logger.error(error);
      setError(GnosisPayError.CONNECTION_FAILED, { message: error.message });
    }
  }

  return {
    checkRegisteredAccounts,
    connect,
    connectedAddress,
    disconnect,
    handleProviderSelection,
    isWalletConnected,
    validateAddress,
  };
}
