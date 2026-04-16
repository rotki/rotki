import type { ComputedRef, Ref } from 'vue';
import { AuthStep, type GnosisPayAdminsMapping, GnosisPayError, type GnosisPayErrorContext } from './types';

interface UseGnosisPayAuthStateReturn {
  checkingRegisteredAccounts: Ref<boolean>;
  clearError: () => void;
  clearValidation: () => void;
  controlledSafeAddresses: Ref<string[]>;
  errorCloseable: ComputedRef<boolean>;
  errorContext: Ref<GnosisPayErrorContext>;
  errorType: Ref<GnosisPayError | null>;
  gnosisPayAdminsMapping: Ref<GnosisPayAdminsMapping>;
  hasRegisteredAccounts: Ref<boolean>;
  isAddressValid: Ref<boolean>;
  resetAuthState: () => void;
  setError: (type: GnosisPayError, context?: GnosisPayErrorContext) => void;
  showNoRegisteredAccountsError: ComputedRef<boolean>;
  signingInProgress: Ref<boolean>;
  signInSuccess: Ref<boolean>;
  validatingAddress: Ref<boolean>;
}

interface UseGnosisPayAuthStepsReturn {
  currentStep: ComputedRef<number>;
  isStepComplete: (step: number) => boolean;
  isStepCurrent: (step: number) => boolean;
}

/**
 * Composable for managing Gnosis Pay authentication state
 */
export function useGnosisPayAuthState(): UseGnosisPayAuthStateReturn {
  const errorType = ref<GnosisPayError | null>(null);
  const errorContext = ref<GnosisPayErrorContext>({});
  const signingInProgress = ref<boolean>(false);
  const validatingAddress = ref<boolean>(false);
  const isAddressValid = ref<boolean>(false);
  const gnosisPayAdminsMapping = ref<GnosisPayAdminsMapping>({});
  const controlledSafeAddresses = ref<string[]>([]);
  const checkingRegisteredAccounts = ref<boolean>(false);
  const hasRegisteredAccounts = ref<boolean>(false);
  const signInSuccess = ref<boolean>(false);

  const errorCloseable = computed<boolean>(() => {
    const type = get(errorType);
    if (!type)
      return true;

    // Non-closeable errors:
    // 1. No registered accounts
    // 2. Connected wallet address is not valid
    return type !== GnosisPayError.NO_REGISTERED_ACCOUNTS
      && type !== GnosisPayError.INVALID_ADDRESS;
  });

  const showNoRegisteredAccountsError = computed<boolean>(
    () => get(errorType) === GnosisPayError.NO_REGISTERED_ACCOUNTS,
  );

  function clearError(): void {
    set(errorType, null);
    set(errorContext, {});
  }

  function clearValidation(): void {
    set(isAddressValid, false);
    set(controlledSafeAddresses, []);
  }

  function setError(type: GnosisPayError, context: GnosisPayErrorContext = {}): void {
    set(errorType, type);
    set(errorContext, context);
  }

  function resetAuthState(): void {
    clearError();
    clearValidation();
    set(signInSuccess, false);
    set(signingInProgress, false);
    set(validatingAddress, false);
  }

  return {
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
    resetAuthState,
    setError,
    showNoRegisteredAccountsError,
    signingInProgress,
    signInSuccess,
    validatingAddress,
  };
}

/**
 * Composable for computing the current authentication step
 */
export function useGnosisPayAuthSteps(
  hasRegisteredAccounts: Ref<boolean>,
  isWalletConnected: Ref<boolean>,
  validatingAddress: Ref<boolean>,
  signInSuccess: Ref<boolean>,
): UseGnosisPayAuthStepsReturn {
  const currentStep = computed<number>(() => {
    // Skip showing the account verification step - it happens in background
    if (!get(hasRegisteredAccounts))
      return AuthStep.NOT_READY;
    if (!get(isWalletConnected))
      return AuthStep.CONNECT_WALLET;
    if (get(validatingAddress))
      return AuthStep.VALIDATE_ADDRESS;
    if (!get(signInSuccess))
      return AuthStep.SIGN_MESSAGE;
    return AuthStep.COMPLETE;
  });

  function isStepComplete(step: number): boolean {
    return get(currentStep) > step;
  }

  function isStepCurrent(step: number): boolean {
    return get(currentStep) === step;
  }

  return {
    currentStep,
    isStepComplete,
    isStepCurrent,
  };
}
