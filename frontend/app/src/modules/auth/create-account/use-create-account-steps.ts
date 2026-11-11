import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { CreateAccountMode, CreateAccountStepId } from '@/modules/auth/create-account/types';
import { externalLinks } from '@shared/external-links';

/** What the side panel says about the screen on show, beside the form rather than inside it. */
interface CreateAccountContext {
  title: string;
  body: string;
  link?: { text: string; url: string };
}

export interface CreateAccountStep {
  id: CreateAccountStepId;
  title: string;
}

interface UseCreateAccountStepsReturn {
  /** The chosen path's steps in order, empty until a path is chosen. */
  steps: ComputedRef<CreateAccountStep[]>;
  /** The step on show, or undefined while the path is still being chosen. */
  current: ComputedRef<CreateAccountStep | undefined>;
  /** The side panel's text for the screen on show, the path choice included. */
  context: ComputedRef<CreateAccountContext>;
}

const FLOWS: Record<CreateAccountMode, readonly CreateAccountStepId[]> = {
  create: ['profile', 'preferences'],
  restore: ['premium', 'profile', 'summary'],
};

/** The 1-based position of a step within a path, or undefined for a step the path does not have. */
export function stepPosition(mode: CreateAccountMode, id: CreateAccountStepId): number | undefined {
  const index = FLOWS[mode].indexOf(id);
  return index === -1 ? undefined : index + 1;
}

/**
 * The wizard's steps for the chosen path, and what the side panel says about each.
 *
 * @remarks
 * Choosing a path is not a step: the count starts once a path is chosen, so it never changes under
 * the user.
 *
 * @param mode - the chosen path, unset while it is being chosen
 * @param step - the 1-based position within the chosen path
 */
export function useCreateAccountSteps(
  mode: MaybeRefOrGetter<CreateAccountMode | undefined>,
  step: MaybeRefOrGetter<number>,
): UseCreateAccountStepsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const titles = computed<Record<CreateAccountStepId, string>>(() => ({
    preferences: t('create_account.steps.preferences.title'),
    premium: t('create_account.steps.premium.title'),
    profile: toValue(mode) === 'restore'
      ? t('create_account.steps.profile.restore_title')
      : t('create_account.steps.profile.title'),
    summary: t('create_account.steps.summary.title'),
  }));

  const steps = computed<CreateAccountStep[]>(() => {
    const selected = toValue(mode);
    if (!selected)
      return [];
    return FLOWS[selected].map(id => ({ id, title: get(titles)[id] }));
  });

  const current = computed<CreateAccountStep | undefined>(() => get(steps)[toValue(step) - 1]);

  const context = computed<CreateAccountContext>(() => {
    const id = get(current)?.id;
    if (id === 'profile' && toValue(mode) === 'restore') {
      return {
        body: t('create_account.context.profile_restore.body'),
        title: t('create_account.context.profile_restore.title'),
      };
    }
    if (id === 'profile') {
      return {
        body: t('create_account.context.profile.body'),
        title: t('create_account.context.profile.title'),
      };
    }
    if (id === 'preferences') {
      return {
        body: t('create_account.context.preferences.body'),
        title: t('create_account.context.preferences.title'),
      };
    }
    if (id === 'premium') {
      return {
        body: t('create_account.context.premium.body'),
        link: { text: t('create_account.context.premium.link'), url: externalLinks.manageSubscriptions },
        title: t('create_account.context.premium.title'),
      };
    }
    if (id === 'summary') {
      return {
        body: t('create_account.context.summary.body'),
        link: { text: t('create_account.context.summary.link'), url: externalLinks.usageGuideSection.moveGlobalDatabase },
        title: t('create_account.context.summary.title'),
      };
    }
    return {
      body: t('create_account.context.entry.body'),
      title: t('create_account.context.entry.title'),
    };
  });

  return { context, current, steps };
}
