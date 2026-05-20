import type { Ref } from 'vue';
import { describe, expect, it } from 'vitest';
import { AuthStep, GnosisPayError } from './types';
import { useGnosisPayAuthState, useGnosisPayAuthSteps } from './use-gnosis-pay-auth-state';

describe('useGnosisPayAuthState', () => {
  it('should initialize with default state', () => {
    const state = useGnosisPayAuthState();

    expect(get(state.errorType)).toBeNull();
    expect(get(state.errorContext)).toEqual({});
    expect(get(state.signingInProgress)).toBe(false);
    expect(get(state.validatingAddress)).toBe(false);
    expect(get(state.isAddressValid)).toBe(false);
    expect(get(state.gnosisPayAdminsMapping)).toEqual({});
    expect(get(state.controlledSafeAddresses)).toEqual([]);
    expect(get(state.checkingRegisteredAccounts)).toBe(false);
    expect(get(state.hasRegisteredAccounts)).toBe(false);
    expect(get(state.signInSuccess)).toBe(false);
    expect(get(state.errorCloseable)).toBe(true);
    expect(get(state.showNoRegisteredAccountsError)).toBe(false);
  });

  describe('errorCloseable', () => {
    it('should be true when there is no error', () => {
      const { errorCloseable } = useGnosisPayAuthState();
      expect(get(errorCloseable)).toBe(true);
    });

    it.each([
      [GnosisPayError.NO_REGISTERED_ACCOUNTS],
      [GnosisPayError.INVALID_ADDRESS],
    ])('should be false for non-closeable error %s', (errorType) => {
      const state = useGnosisPayAuthState();
      state.setError(errorType);
      expect(get(state.errorCloseable)).toBe(false);
    });

    it.each([
      [GnosisPayError.NO_WALLET_CONNECTED],
      [GnosisPayError.SIGNATURE_REJECTED],
      [GnosisPayError.CONNECTION_FAILED],
      [GnosisPayError.OTHER],
    ])('should be true for closeable error %s', (errorType) => {
      const state = useGnosisPayAuthState();
      state.setError(errorType);
      expect(get(state.errorCloseable)).toBe(true);
    });
  });

  describe('showNoRegisteredAccountsError', () => {
    it('should be true only when the error type is NO_REGISTERED_ACCOUNTS', () => {
      const state = useGnosisPayAuthState();

      state.setError(GnosisPayError.NO_REGISTERED_ACCOUNTS);
      expect(get(state.showNoRegisteredAccountsError)).toBe(true);

      state.setError(GnosisPayError.INVALID_ADDRESS);
      expect(get(state.showNoRegisteredAccountsError)).toBe(false);
    });
  });

  describe('setError', () => {
    it('should store the error type and context', () => {
      const state = useGnosisPayAuthState();
      state.setError(GnosisPayError.OTHER, { message: 'oops' });

      expect(get(state.errorType)).toBe(GnosisPayError.OTHER);
      expect(get(state.errorContext)).toEqual({ message: 'oops' });
    });

    it('should default to an empty context when none is provided', () => {
      const state = useGnosisPayAuthState();
      state.setError(GnosisPayError.SIGNATURE_REJECTED);

      expect(get(state.errorContext)).toEqual({});
    });
  });

  describe('clearError', () => {
    it('should reset errorType and errorContext', () => {
      const state = useGnosisPayAuthState();
      state.setError(GnosisPayError.OTHER, { message: 'oops' });

      state.clearError();

      expect(get(state.errorType)).toBeNull();
      expect(get(state.errorContext)).toEqual({});
    });
  });

  describe('clearValidation', () => {
    it('should reset address validation state', () => {
      const state = useGnosisPayAuthState();
      set(state.isAddressValid, true);
      set(state.controlledSafeAddresses, ['0xsafe']);

      state.clearValidation();

      expect(get(state.isAddressValid)).toBe(false);
      expect(get(state.controlledSafeAddresses)).toEqual([]);
    });
  });

  describe('resetAuthState', () => {
    it('should clear error, validation, sign-in success and progress flags', () => {
      const state = useGnosisPayAuthState();
      state.setError(GnosisPayError.OTHER, { message: 'oops' });
      set(state.isAddressValid, true);
      set(state.controlledSafeAddresses, ['0xsafe']);
      set(state.signInSuccess, true);
      set(state.signingInProgress, true);
      set(state.validatingAddress, true);

      state.resetAuthState();

      expect(get(state.errorType)).toBeNull();
      expect(get(state.errorContext)).toEqual({});
      expect(get(state.isAddressValid)).toBe(false);
      expect(get(state.controlledSafeAddresses)).toEqual([]);
      expect(get(state.signInSuccess)).toBe(false);
      expect(get(state.signingInProgress)).toBe(false);
      expect(get(state.validatingAddress)).toBe(false);
    });
  });
});

describe('useGnosisPayAuthSteps', () => {
  interface StepsOverrides {
    hasRegisteredAccounts?: boolean;
    isWalletConnected?: boolean;
    validatingAddress?: boolean;
    signInSuccess?: boolean;
  }

  function createSteps(overrides: StepsOverrides = {}): {
    hasRegisteredAccounts: Ref<boolean>;
    isWalletConnected: Ref<boolean>;
    signInSuccess: Ref<boolean>;
    steps: ReturnType<typeof useGnosisPayAuthSteps>;
    validatingAddress: Ref<boolean>;
  } {
    const hasRegisteredAccounts = ref<boolean>(overrides.hasRegisteredAccounts ?? false);
    const isWalletConnected = ref<boolean>(overrides.isWalletConnected ?? false);
    const validatingAddress = ref<boolean>(overrides.validatingAddress ?? false);
    const signInSuccess = ref<boolean>(overrides.signInSuccess ?? false);
    const steps = useGnosisPayAuthSteps(hasRegisteredAccounts, isWalletConnected, validatingAddress, signInSuccess);
    return { hasRegisteredAccounts, isWalletConnected, signInSuccess, steps, validatingAddress };
  }

  it('should report NOT_READY when there are no registered accounts', () => {
    const { steps } = createSteps({ hasRegisteredAccounts: false });
    expect(get(steps.currentStep)).toBe(AuthStep.NOT_READY);
  });

  it('should report CONNECT_WALLET when accounts exist but wallet not connected', () => {
    const { steps } = createSteps({ hasRegisteredAccounts: true, isWalletConnected: false });
    expect(get(steps.currentStep)).toBe(AuthStep.CONNECT_WALLET);
  });

  it('should report VALIDATE_ADDRESS while validating', () => {
    const { steps } = createSteps({
      hasRegisteredAccounts: true,
      isWalletConnected: true,
      validatingAddress: true,
    });
    expect(get(steps.currentStep)).toBe(AuthStep.VALIDATE_ADDRESS);
  });

  it('should report SIGN_MESSAGE when validated but not signed in', () => {
    const { steps } = createSteps({
      hasRegisteredAccounts: true,
      isWalletConnected: true,
      signInSuccess: false,
      validatingAddress: false,
    });
    expect(get(steps.currentStep)).toBe(AuthStep.SIGN_MESSAGE);
  });

  it('should report COMPLETE when signed in', () => {
    const { steps } = createSteps({
      hasRegisteredAccounts: true,
      isWalletConnected: true,
      signInSuccess: true,
      validatingAddress: false,
    });
    expect(get(steps.currentStep)).toBe(AuthStep.COMPLETE);
  });

  it('should react when source refs change', () => {
    const { hasRegisteredAccounts, isWalletConnected, steps } = createSteps();
    expect(get(steps.currentStep)).toBe(AuthStep.NOT_READY);

    set(hasRegisteredAccounts, true);
    expect(get(steps.currentStep)).toBe(AuthStep.CONNECT_WALLET);

    set(isWalletConnected, true);
    expect(get(steps.currentStep)).toBe(AuthStep.SIGN_MESSAGE);
  });

  describe('isStepComplete / isStepCurrent', () => {
    it('should identify steps before currentStep as complete', () => {
      const { steps } = createSteps({
        hasRegisteredAccounts: true,
        isWalletConnected: true,
        signInSuccess: false,
      });
      // currentStep === SIGN_MESSAGE (3)
      expect(steps.isStepComplete(AuthStep.NOT_READY)).toBe(true);
      expect(steps.isStepComplete(AuthStep.CONNECT_WALLET)).toBe(true);
      expect(steps.isStepComplete(AuthStep.VALIDATE_ADDRESS)).toBe(true);
      expect(steps.isStepComplete(AuthStep.SIGN_MESSAGE)).toBe(false);
    });

    it('should identify only the matching step as current', () => {
      const { steps } = createSteps({
        hasRegisteredAccounts: true,
        isWalletConnected: false,
      });
      expect(steps.isStepCurrent(AuthStep.CONNECT_WALLET)).toBe(true);
      expect(steps.isStepCurrent(AuthStep.SIGN_MESSAGE)).toBe(false);
    });
  });
});
