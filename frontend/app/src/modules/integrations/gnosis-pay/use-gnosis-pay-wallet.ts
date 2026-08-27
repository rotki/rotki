import type { ComputedRef, Ref } from 'vue';
import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useProviderSelection } from '@/modules/wallet/providers/use-provider-selection';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';
import { type GnosisPayAdminsMapping, GnosisPayError, type GnosisPayErrorContext } from './types';
import { useGnosisPaySiweApi } from './use-gnosis-pay-api';

interface UseGnosisPayWalletOptions {
  /** Owned by `useGnosisPayAuthState`, toggled here around the admins fetch so the auth card can show its "checking accounts" alert. */
  checkingRegisteredAccounts: Ref<boolean>;
  /** Resets the shared error type and context. Called at the start of every wallet action so a stale error never survives a retry. */
  clearError: () => void;
  /** Drops `isAddressValid` and `controlledSafeAddresses`. Called before re-validating and again if validation throws. */
  clearValidation: () => void;
  /** Written only on a successful validation, with every safe address the connected admin address controls. */
  controlledSafeAddresses: Ref<string[]>;
  /** Safe address to admin addresses, filled by `checkRegisteredAccounts` and read back by `validateAddress` to match the connected wallet. */
  gnosisPayAdminsMapping: Ref<GnosisPayAdminsMapping>;
  /** False until the backend reports at least one registered Gnosis Pay safe. Gates whether the step flow renders at all. */
  hasRegisteredAccounts: Ref<boolean>;
  /** Only ever set to true here, when the connected address is an admin of at least one safe. Clearing it is `clearValidation`'s job. */
  isAddressValid: Ref<boolean>;
  /** Stores the error the auth component maps to a localized message. The context carries the extras it needs (`message`, `adminsMapping`). */
  setError: (type: GnosisPayError, context?: GnosisPayErrorContext) => void;
  /** Toggled around `validateAddress`, driving both the validation step spinner and the current-step computation. */
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
    catch (error: unknown) {
      set(hasRegisteredAccounts, false);
      logger.error('Failed to check registered accounts:', error);
      setError(GnosisPayError.OTHER, { message: getErrorMessage(error) });
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
    catch (error: unknown) {
      clearValidation();
      logger.error('Address validation failed:', error);
      setError(GnosisPayError.OTHER, { message: getErrorMessage(error) });
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
    }
    catch (error: unknown) {
      logger.error(error);
      setError(GnosisPayError.CONNECTION_FAILED, { message: getErrorMessage(error) });
    }
  }

  async function disconnect(): Promise<void> {
    try {
      clearError();
      clearValidation();
      await disconnectWallet();
    }
    catch (error: unknown) {
      logger.error(error);
      setError(GnosisPayError.CONNECTION_FAILED, { message: getErrorMessage(error) });
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
