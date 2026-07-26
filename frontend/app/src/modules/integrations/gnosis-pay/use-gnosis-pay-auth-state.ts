import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { AuthStep, type GnosisPayAdminsMapping, GnosisPayError, type GnosisPayErrorContext } from './types';

interface UseGnosisPayAuthStateReturn {
  checkingRegisteredAccounts: Ref<boolean>;
  clearError: () => void;
  clearValidation: () => void;
  controlledSafeAddresses: Ref<string[]>;
  errorCloseable: ComputedRef<boolean>;
  errorContext: Readonly<Ref<GnosisPayErrorContext>>;
  errorType: Readonly<Ref<GnosisPayError | null>>;
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
  const errorType = shallowRef<GnosisPayError | null>(null);
  const errorContext = ref<GnosisPayErrorContext>({});
  const modelSigningInProgress = shallowRef<boolean>(false);
  const modelValidatingAddress = shallowRef<boolean>(false);
  const modelIsAddressValid = shallowRef<boolean>(false);
  const modelGnosisPayAdminsMapping = ref<GnosisPayAdminsMapping>({});
  const modelControlledSafeAddresses = ref<string[]>([]);
  const modelCheckingRegisteredAccounts = shallowRef<boolean>(false);
  const modelHasRegisteredAccounts = shallowRef<boolean>(false);
  const modelSignInSuccess = shallowRef<boolean>(false);

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
    set(modelIsAddressValid, false);
    set(modelControlledSafeAddresses, []);
  }

  function setError(type: GnosisPayError, context: GnosisPayErrorContext = {}): void {
    set(errorType, type);
    set(errorContext, context);
  }

  function resetAuthState(): void {
    clearError();
    clearValidation();
    set(modelSignInSuccess, false);
    set(modelSigningInProgress, false);
    set(modelValidatingAddress, false);
  }

  return {
    checkingRegisteredAccounts: modelCheckingRegisteredAccounts,
    clearError,
    clearValidation,
    controlledSafeAddresses: modelControlledSafeAddresses,
    errorCloseable,
    errorContext: shallowReadonly(errorContext),
    errorType: readonly(errorType),
    gnosisPayAdminsMapping: modelGnosisPayAdminsMapping,
    hasRegisteredAccounts: modelHasRegisteredAccounts,
    isAddressValid: modelIsAddressValid,
    resetAuthState,
    setError,
    showNoRegisteredAccountsError,
    signingInProgress: modelSigningInProgress,
    signInSuccess: modelSignInSuccess,
    validatingAddress: modelValidatingAddress,
  };
}

/**
 * Composable for computing the current authentication step
 */
export function useGnosisPayAuthSteps(
  hasRegisteredAccounts: MaybeRefOrGetter<boolean>,
  isWalletConnected: MaybeRefOrGetter<boolean>,
  validatingAddress: MaybeRefOrGetter<boolean>,
  signInSuccess: MaybeRefOrGetter<boolean>,
): UseGnosisPayAuthStepsReturn {
  const currentStep = computed<number>(() => {
    // Skip showing the account verification step - it happens in background
    if (!toValue(hasRegisteredAccounts))
      return AuthStep.NOT_READY;
    if (!toValue(isWalletConnected))
      return AuthStep.CONNECT_WALLET;
    if (toValue(validatingAddress))
      return AuthStep.VALIDATE_ADDRESS;
    if (!toValue(signInSuccess))
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
