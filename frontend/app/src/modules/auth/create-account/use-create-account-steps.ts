import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { CreateAccountMode } from '@/modules/auth/create-account/types';

interface CreateAccountStep {
  title: string;
  description?: string;
}

interface UseCreateAccountStepsReturn {
  steps: ComputedRef<CreateAccountStep[]>;
}

/**
 * The wizard's steps, worded for the chosen mode.
 *
 * @remarks
 * Shared by the side stepper and the wizard's own heading, so the two always name the step alike.
 *
 * @param mode - the mode picked on the first step, if any
 */
export function useCreateAccountSteps(mode: MaybeRefOrGetter<CreateAccountMode | undefined>): UseCreateAccountStepsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const steps = computed<CreateAccountStep[]>(() => {
    const restore = toValue(mode) === 'restore';
    return [
      {
        description: t('create_account.steps.step_1.description'),
        title: t('create_account.steps.step_1.title'),
      },
      {
        description: restore
          ? t('create_account.steps.step_2.restore_description')
          : t('create_account.steps.step_2.description'),
        title: restore
          ? t('create_account.steps.step_2.restore_title')
          : t('create_account.steps.step_2.title'),
      },
      {
        description: t('create_account.steps.step_3.description'),
        title: restore
          ? t('create_account.steps.step_3.restore_title')
          : t('create_account.steps.step_3.title'),
      },
      {
        title: t('create_account.steps.step_4.title'),
      },
    ];
  });

  return { steps };
}
