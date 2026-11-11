import type { Ref } from 'vue';
import type { SupportedCurrency } from '@/modules/assets/amount-display/currencies';
import type { CreateAccountMode, CreateAccountStepId } from '@/modules/auth/create-account/types';
import type { CreateAccountPayload, LoginCredentials, PremiumSetup } from '@/modules/auth/login';
import { suggestCurrency } from '@/modules/auth/create-account/locale-currency';
import { stepPosition } from '@/modules/auth/create-account/use-create-account-steps';

interface UseCreateAccountWizardReturn {
  /** Whether premium credentials are being given: the opened premium section, or always on restore. */
  modelPremiumEnabled: Ref<boolean>;
  /** The premium credentials, and whether the database is downloaded from them. */
  modelPremiumSetupForm: Ref<PremiumSetup>;
  /** Whether a newly created premium profile turns on automatic backups. */
  modelPremiumShouldSync: Ref<boolean>;
  /** The username and password the account is created with. */
  modelCredentialsForm: Ref<LoginCredentials>;
  /** The repeated password, checked against the one in the credentials form. */
  modelPasswordConfirm: Ref<string>;
  /** Whether the user has acknowledged that a lost password cannot be recovered. */
  modelUserPrompted: Ref<boolean>;
  /** The currency a created profile starts in, suggested from the system locale until the user picks. */
  modelMainCurrency: Ref<SupportedCurrency>;
  /** Whether anonymous usage analytics are submitted. */
  modelSubmitUsageAnalytics: Ref<boolean>;
  /** Moves to the following step. */
  nextStep: () => void;
  /** Moves back one step, returning to the path choice from the first one. */
  prevStep: () => void;
  /** Jumps back to an earlier step of the chosen path. */
  goToStep: (id: CreateAccountStepId) => void;
  /** Answers the path choice and moves to the path's first step. */
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
 * @param step - the 1-based position within the chosen path, shared with the page
 * @param mode - whether the account is created or restored, unset while the path is being chosen
 * @returns the per-step forms plus the transitions between the steps
 */
export function useCreateAccountWizard(
  step: Ref<number>,
  mode: Ref<CreateAccountMode | undefined>,
): UseCreateAccountWizardReturn {
  const modelPremiumEnabled = shallowRef<boolean>(false);
  const modelPremiumSetupForm = ref<PremiumSetup>(emptyPremiumSetup());
  const modelPremiumShouldSync = shallowRef<boolean>(false);
  const modelCredentialsForm = ref<LoginCredentials>({ password: '', username: '' });
  const modelPasswordConfirm = shallowRef<string>('');
  const modelUserPrompted = shallowRef<boolean>(false);
  const systemLocale = typeof navigator === 'undefined' ? '' : navigator.language;
  const modelMainCurrency = shallowRef<SupportedCurrency>(suggestCurrency(systemLocale));
  const modelSubmitUsageAnalytics = shallowRef<boolean>(true);

  function resetPremium(): void {
    set(modelPremiumEnabled, false);
    set(modelPremiumSetupForm, emptyPremiumSetup());
    set(modelPremiumShouldSync, false);
  }

  function nextStep(): void {
    set(step, get(step) + 1);
  }

  /**
   * A password typed for one path is not the password the other path needs: a new profile picks its
   * own, a restore must use the synced profile's. The profile name may stay.
   */
  function resetPassword(): void {
    set(modelCredentialsForm, { ...get(modelCredentialsForm), password: '' });
    set(modelPasswordConfirm, '');
    set(modelUserPrompted, false);
  }

  /**
   * @remarks
   * Leaving the first step means the path is being chosen again, so the premium answers are dropped
   * (a restore seeds them, and keeping them would carry a database download into a plain create) and
   * so is the password.
   */
  function prevStep(): void {
    if (get(step) > 1) {
      set(step, get(step) - 1);
      return;
    }
    set(mode, undefined);
    set(step, 1);
    resetPremium();
    resetPassword();
  }

  /** A step the chosen path does not have is ignored, rather than leaving the wizard on no step. */
  function goToStep(id: CreateAccountStepId): void {
    const selected = get(mode);
    const position = selected ? stepPosition(selected, id) : undefined;
    if (position)
      set(step, position);
  }

  /** Restoring is restoring from the premium sync, so both are answered as soon as it is chosen. */
  function selectMode(selected: CreateAccountMode): void {
    resetPremium();
    set(mode, selected);
    set(step, 1);
    if (selected === 'restore') {
      set(modelPremiumEnabled, true);
      set(modelPremiumSetupForm, { ...emptyPremiumSetup(), syncDatabase: true });
    }
  }

  /**
   * On create, an opened premium section with both fields left empty counts as no premium.
   *
   * @remarks
   * A restore sends no settings: the downloaded database replaces the one they would be written to,
   * so the backup's own currency, analytics and backup choices are the ones that apply.
   */
  function buildPayload(): CreateAccountPayload {
    const premium = get(modelPremiumSetupForm);
    const restore = get(mode) === 'restore';
    const withPremium = restore
      || (get(modelPremiumEnabled) && premium.apiKey !== '' && premium.apiSecret !== '');

    const initialSettings: CreateAccountPayload['initialSettings'] = restore
      ? {}
      : {
          mainCurrency: get(modelMainCurrency),
          submitUsageAnalytics: get(modelSubmitUsageAnalytics),
          ...(withPremium && get(modelPremiumShouldSync) ? { premiumShouldSync: true } : {}),
        };

    const payload: CreateAccountPayload = {
      credentials: get(modelCredentialsForm),
      initialSettings,
    };

    if (withPremium)
      payload.premiumSetup = premium;

    return payload;
  }

  return {
    buildPayload,
    goToStep,
    modelCredentialsForm,
    modelMainCurrency,
    modelPasswordConfirm,
    modelPremiumEnabled,
    modelPremiumSetupForm,
    modelPremiumShouldSync,
    modelSubmitUsageAnalytics,
    modelUserPrompted,
    nextStep,
    prevStep,
    selectMode,
  };
}
