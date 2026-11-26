import type { MaybePromise } from '@rotki/common';
import type { EnhancedProviderDetail } from '@/modules/wallet/providers/provider-detection';
import { logicNot, logicOr } from '@vueuse/math';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type Ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { AuthStep, GnosisPayError, type GnosisPayErrorContext } from './types';
import { useGnosisPayAuthState, useGnosisPayAuthSteps } from './use-gnosis-pay-auth-state';
import { useGnosisPaySigning } from './use-gnosis-pay-signing';
import { useGnosisPayWallet } from './use-gnosis-pay-wallet';
import { GNOSIS_CHAIN_ID, useGnosisPayWalletStatus } from './use-gnosis-pay-wallet-status';

interface UseGnosisPaySignInOptions {
  /** Awaited once the backend confirms the signature. The auth card uses it to reload the API key and re-check the safe migration. */
  onSignInComplete: () => MaybePromise<void>;
}

interface UseGnosisPaySignInReturn {
  availableProviders: Readonly<Ref<EnhancedProviderDetail[]>>;
  checkingRegisteredAccounts: Ref<boolean>;
  checkRegisteredAccounts: () => Promise<void>;
  clearError: () => void;
  clearValidation: () => void;
  connectedAddress: Ref<string | undefined>;
  /** The Safes the session covers: those the signing wallet controls, else every tracked one. */
  connectedSafes: ComputedRef<string[]>;
  connectionErrorMessage: ComputedRef<string>;
  controlledSafeAddresses: Ref<string[]>;
  detectingProviders: Readonly<Ref<boolean>>;
  disconnect: () => Promise<void>;
  errorCloseable: ComputedRef<boolean>;
  errorContext: Readonly<Ref<GnosisPayErrorContext>>;
  errorType: Readonly<Ref<GnosisPayError | null>>;
  /** Moves the wizard back to an earlier step by clearing what that step decided; a later step is ignored. */
  goToStep: (step: number) => Promise<void>;
  handleProviderSelection: (provider: EnhancedProviderDetail) => Promise<void>;
  hasRegisteredAccounts: Ref<boolean>;
  isAddressValid: Ref<boolean>;
  isConnecting: ComputedRef<boolean>;
  isDisconnecting: Ref<boolean>;
  isOnGnosisChain: ComputedRef<boolean>;
  isStepComplete: (step: number) => boolean;
  isStepCurrent: (step: number) => boolean;
  isWalletConnect: ComputedRef<boolean>;
  isWalletConnected: ComputedRef<boolean>;
  /** Whether the provider picker is open; the template binds it with `v-model`. */
  modelShowProviderSelection: Ref<boolean>;
  /** Stops the signing spinner. */
  cancelSigning: () => void;
  /** Disconnects a connected wallet, connects otherwise. */
  onConnectClicked: () => Promise<void>;
  primaryActionDisabled: ComputedRef<boolean>;
  showNoRegisteredAccountsError: ComputedRef<boolean>;
  signingInProgress: Ref<boolean>;
  signInSuccess: Ref<boolean>;
  signInWithEthereum: () => Promise<void>;
  switchingNetwork: Readonly<Ref<boolean>>;
  switchToGnosis: () => Promise<void>;
  validateAddress: () => Promise<void>;
  validatingAddress: Ref<boolean>;
  validationErrorMessage: ComputedRef<string>;
}

/**
 * The Gnosis Pay sign-in flow: auth state, wallet connection, address validation and SIWE signing,
 * wired together with the step the wizard is on.
 *
 * @remarks
 * Creates its own auth state on every call, so call it once per sign-in card.
 */
export function useGnosisPaySignIn(options: UseGnosisPaySignInOptions): UseGnosisPaySignInReturn {
  const { onSignInComplete } = options;
  const { t } = useI18n({ useScope: 'global' });

  const authState = useGnosisPayAuthState();
  const {
    checkingRegisteredAccounts,
    clearError,
    clearValidation,
    controlledSafeAddresses,
    errorCloseable,
    errorContext,
    errorType,
    gnosisPayAdminsMapping,
    hasRegisteredAccounts,
    isAddressValid,
    setError,
    showNoRegisteredAccountsError,
    signingInProgress,
    signInSuccess,
    validatingAddress,
  } = authState;

  /** The Safes the session covers: those the signing wallet controls, else every tracked one. */
  const connectedSafes = computed<string[]>(() => {
    const controlled = get(controlledSafeAddresses);
    return controlled.length > 0 ? controlled : Object.keys(get(gnosisPayAdminsMapping));
  });

  const wallet = useGnosisPayWallet({
    checkingRegisteredAccounts,
    clearError,
    clearValidation,
    controlledSafeAddresses,
    gnosisPayAdminsMapping,
    hasRegisteredAccounts,
    isAddressValid,
    setError,
    validatingAddress,
  });

  const {
    checkRegisteredAccounts,
    connect,
    connectedAddress,
    disconnect,
    handleProviderSelection,
    isWalletConnected,
    switchingNetwork,
    switchToChain,
    validateAddress,
  } = wallet;

  const signing = useGnosisPaySigning({
    clearError,
    connectedAddress,
    errorType,
    onSignInComplete,
    setError,
    signingInProgress,
    signInSuccess,
  });

  const { signInWithEthereum } = signing;

  const { currentStep, isStepComplete, isStepCurrent } = useGnosisPayAuthSteps(
    hasRegisteredAccounts,
    isWalletConnected,
    validatingAddress,
    signInSuccess,
  );

  const {
    availableProviders,
    detectingProviders,
    isConnecting,
    isDisconnecting,
    isOnGnosisChain,
    isWalletConnect,
    showProviderSelection: modelShowProviderSelection,
  } = useGnosisPayWalletStatus();

  // Separate error messages for different steps
  const connectionErrorMessage = computed<string>(() => {
    const type = get(errorType);
    if (!type)
      return '';

    const context = get(errorContext);

    switch (type) {
      case GnosisPayError.NO_WALLET_CONNECTED:
        return t('external_services.gnosispay.errors.no_wallet_connected');
      case GnosisPayError.CONNECTION_FAILED:
        // An empty message falls back too.
        if (context.message)
          return context.message;
        return t('external_services.gnosispay.errors.connection_failed');
      case GnosisPayError.INVALID_ADDRESS:
      case GnosisPayError.NO_REGISTERED_ACCOUNTS:
      case GnosisPayError.OTHER:
      case GnosisPayError.SIGNATURE_REJECTED:
        return '';
    }
  });

  const validationErrorMessage = computed<string>(() => {
    const type = get(errorType);
    if (!type)
      return '';

    const context = get(errorContext);

    switch (type) {
      case GnosisPayError.INVALID_ADDRESS:
        return t('external_services.gnosispay.errors.invalid_address');
      case GnosisPayError.SIGNATURE_REJECTED:
        return t('external_services.gnosispay.errors.signature_rejected');
      case GnosisPayError.OTHER:
        // An empty message falls back too.
        if (context.message)
          return context.message;
        return t('external_services.gnosispay.errors.unknown');
      case GnosisPayError.CONNECTION_FAILED:
      case GnosisPayError.NO_REGISTERED_ACCOUNTS:
      case GnosisPayError.NO_WALLET_CONNECTED:
        return '';
    }
  });

  const primaryActionDisabled = logicOr(signingInProgress, logicNot(connectedAddress), logicNot(isOnGnosisChain));

  async function switchToGnosis(): Promise<void> {
    await switchToChain(GNOSIS_CHAIN_ID);
  }

  function cancelSigning(): void {
    set(signingInProgress, false);
  }

  async function onConnectClicked(): Promise<void> {
    if (get(isWalletConnected))
      await disconnect();
    else
      await connect();
  }

  async function goToStep(step: number): Promise<void> {
    const current = get(currentStep);

    if (step >= current)
      return;

    // Navigate to the requested step by clearing state
    if (step === AuthStep.CONNECT_WALLET) {
      // Go back to Step 1: disconnect wallet
      if (get(isWalletConnected))
        await disconnect();
    }
    else if (step === AuthStep.VALIDATE_ADDRESS) {
      // Go back to Step 2: clear validation
      clearValidation();
      clearError();
    }
  }

  return {
    availableProviders,
    cancelSigning,
    checkingRegisteredAccounts,
    checkRegisteredAccounts,
    clearError,
    clearValidation,
    connectedAddress,
    connectedSafes,
    connectionErrorMessage,
    controlledSafeAddresses,
    detectingProviders,
    disconnect,
    errorCloseable,
    errorContext,
    errorType,
    goToStep,
    handleProviderSelection,
    hasRegisteredAccounts,
    isAddressValid,
    isConnecting,
    isDisconnecting,
    isOnGnosisChain,
    isStepComplete,
    isStepCurrent,
    isWalletConnect,
    isWalletConnected,
    modelShowProviderSelection,
    onConnectClicked,
    primaryActionDisabled,
    showNoRegisteredAccountsError,
    signingInProgress,
    signInSuccess,
    signInWithEthereum,
    switchingNetwork,
    switchToGnosis,
    validateAddress,
    validatingAddress,
    validationErrorMessage,
  };
}
