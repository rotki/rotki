import type { ComputedRef, Ref } from 'vue';
import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import type { CreateAccountPayload, LoginCredentials, PremiumSetup } from '@/modules/auth/login';

interface UseCreateAccountWizardReturn {
  /** Whether the account is being given premium credentials. */
  modelPremiumEnabled: Ref<boolean>;
  /** The premium credentials, and whether the database is synced from them. */
  modelPremiumSetupForm: Ref<PremiumSetup>;
  /** The username and password the account is created with. */
  modelCredentialsForm: Ref<LoginCredentials>;
  /** The repeated password, checked against the one in the credentials form. */
  modelPasswordConfirm: Ref<string>;
  /** Whether the user has been warned that a lost password cannot be recovered. */
  modelUserPrompted: Ref<boolean>;
  /** Whether anonymous usage analytics are submitted. */
  modelSubmitUsageAnalytics: Ref<boolean>;
  /** Whether the account is being restored rather than created. */
  isRestoreMode: ComputedRef<boolean>;
  /** Moves to the following step. */
  nextStep: () => void;
  /** Moves back one step, forgetting the mode when the first step is reached again. */
  prevStep: () => void;
  /** Answers the first step and moves on. */
  selectMode: (selected: CreateAccountMode) => void;
  /** Collects the answers into the payload the account is created from. */
  buildPayload: () => CreateAccountPayload;
}

function emptyPremiumSetup(): PremiumSetup {
  return { apiKey: '', apiSecret: '', syncDatabase: false };
}

/**
 * The state the create-account wizard carries between its steps, and the transitions that move it.
 *
 * @remarks
 * The wizard owns the answers rather than the steps, because a step is unmounted while another one
 * is showing: going back and forward again has to find what was typed still there.
 *
 * @param step - the wizard's current step, 1-based, shared with the page's stepper
 * @param mode - whether the account is created or restored, unset until the first step answers
 * @returns the per-step forms plus the transitions between the steps
 */
export function useCreateAccountWizard(
  step: Ref<number>,
  mode: Ref<CreateAccountMode | undefined>,
): UseCreateAccountWizardReturn {
  const modelPremiumEnabled = shallowRef<boolean>(false);
  const modelPremiumSetupForm = ref<PremiumSetup>(emptyPremiumSetup());
  const modelCredentialsForm = ref<LoginCredentials>({ password: '', username: '' });
  const modelPasswordConfirm = shallowRef<string>('');
  const modelUserPrompted = shallowRef<boolean>(false);
  const modelSubmitUsageAnalytics = shallowRef<boolean>(true);

  const isRestoreMode = computed<boolean>(() => get(mode) === 'restore');

  function nextStep(): void {
    set(step, get(step) + 1);
  }

  /**
   * @remarks
   * Landing back on the first step means the mode is being chosen again, so the premium answers
   * seeded by the previous choice are dropped: a restore seeds them, and keeping them would carry
   * a database sync into a plain create.
   */
  function prevStep(): void {
    const next = get(step) - 1;
    set(step, next);
    if (next === 1) {
      set(mode, undefined);
      set(modelPremiumEnabled, false);
      set(modelPremiumSetupForm, emptyPremiumSetup());
    }
  }

  /** Restoring an account is restoring it from the premium sync, so both are answered up front. */
  function selectMode(selected: CreateAccountMode): void {
    set(mode, selected);
    if (selected === 'restore') {
      set(modelPremiumEnabled, true);
      set(modelPremiumSetupForm, { ...get(modelPremiumSetupForm), syncDatabase: true });
    }
    nextStep();
  }

  /** The premium credentials are only sent when the user asked for premium. */
  function buildPayload(): CreateAccountPayload {
    const payload: CreateAccountPayload = {
      credentials: get(modelCredentialsForm),
      initialSettings: {
        submitUsageAnalytics: get(modelSubmitUsageAnalytics),
      },
    };

    if (get(modelPremiumEnabled))
      payload.premiumSetup = get(modelPremiumSetupForm);

    return payload;
  }

  return {
    buildPayload,
    isRestoreMode,
    modelCredentialsForm,
    modelPasswordConfirm,
    modelPremiumEnabled,
    modelPremiumSetupForm,
    modelSubmitUsageAnalytics,
    modelUserPrompted,
    nextStep,
    prevStep,
    selectMode,
  };
}
