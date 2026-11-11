<script lang="ts" setup>
import type { CreateAccountMode, CreateAccountStepId } from '@/modules/auth/create-account/types';
import type { CreateAccountPayload } from '@/modules/auth/login';
import { externalLinks } from '@shared/external-links';
import CreateAccountProgress from '@/modules/auth/create-account/CreateAccountProgress.vue';
import CreateAccountCredentials
  from '@/modules/auth/create-account/credentials/CreateAccountCredentials.vue';
import CreateAccountIntroduction
  from '@/modules/auth/create-account/introduction/CreateAccountIntroduction.vue';
import CreateAccountPreferences
  from '@/modules/auth/create-account/preferences/CreateAccountPreferences.vue';
import CreateAccountPremium from '@/modules/auth/create-account/premium/CreateAccountPremium.vue';
import CreateAccountRestoreSummary
  from '@/modules/auth/create-account/summary/CreateAccountRestoreSummary.vue';
import { useCreateAccountSteps } from '@/modules/auth/create-account/use-create-account-steps';
import { useCreateAccountWizard } from '@/modules/auth/create-account/use-create-account-wizard';
import { useStepTransition } from '@/modules/auth/create-account/use-step-transition';
import { useSavedProfiles } from '@/modules/auth/use-saved-profiles';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const step = defineModel<number>('step', { required: true });
const mode = defineModel<CreateAccountMode | undefined>('mode', { default: undefined });

const {
  error = '',
  loading,
} = defineProps<{
  loading: boolean;
  error?: string;
}>();

const emit = defineEmits<{
  'cancel': [];
  'confirm': [payload: CreateAccountPayload];
  'clear-error': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
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
  prevStep: rewind,
  selectMode,
} = useCreateAccountWizard(step, mode);

const { hasProfiles, loadProfiles } = useSavedProfiles();
const { current, steps } = useCreateAccountSteps(mode, step);

const root = useTemplateRef<HTMLElement>('root');
const heading = useTemplateRef<HTMLElement>('heading');

/** Keys the step transition, so moving between steps swaps the content in one go. */
const screen = computed<CreateAccountStepId | 'entry'>(() => get(current)?.id ?? 'entry');

const title = computed<string>(() => get(current)?.title ?? t('create_account.entry.title'));

const { classes: stepTransition } = useStepTransition(() => (get(current) ? get(step) : 0));

/** The error belongs to the submit the user is stepping away from, so leaving the step clears it. */
function clearError(): void {
  if (error)
    emit('clear-error');
}

function prevStep(): void {
  rewind();
  clearError();
}

function goTo(id: CreateAccountStepId): void {
  goToStep(id);
  clearError();
}

function confirm(): void {
  emit('confirm', buildPayload());
}

/** A step entered after scrolling down to the previous one's buttons starts at its top, not mid-way. */
function revealTop(): void {
  get(root)?.scrollIntoView({ block: 'nearest' });
}

/**
 * Hands focus to the new step's heading once the button that moved here has gone with the old step.
 *
 * @remarks
 * A step that already focused one of its own fields, such as the profile name, keeps that focus.
 */
function settleFocus(): void {
  const container = get(root);
  if (container && !container.contains(document.activeElement))
    get(heading)?.focus({ preventScroll: true });
}

onBeforeMount(loadProfiles);
</script>

<template>
  <div
    ref="root"
    class="relative w-full max-w-120 mx-auto scroll-mt-16"
  >
    <CreateAccountProgress
      :steps="steps"
      :step="step"
      :current="current"
    />
    <Transition
      mode="out-in"
      :enter-from-class="stepTransition.enterFromClass"
      enter-active-class="transition duration-200 ease-out motion-reduce:transition-none"
      :leave-to-class="stepTransition.leaveToClass"
      leave-active-class="transition duration-100 ease-in motion-reduce:transition-none"
      @before-enter="revealTop()"
      @after-enter="settleFocus()"
    >
      <div
        :key="screen"
        :data-testid="`create-account-screen-${screen}`"
      >
        <h1
          ref="heading"
          tabindex="-1"
          class="text-h4 mb-6 outline-none"
          data-testid="create-account-heading"
        >
          {{ title }}
        </h1>
        <div
          v-if="screen === 'entry'"
          class="flex flex-col gap-6"
        >
          <i18n-t
            scope="global"
            keypath="create_account.entry.description"
            class="text-body-1 text-rui-text-secondary"
            tag="p"
          >
            <template #documentation>
              <ExternalLink
                :text="t('login.description.learn_more')"
                :url="externalLinks.usageGuide"
              />
            </template>
          </i18n-t>
          <CreateAccountIntroduction @select="selectMode($event)" />
          <div
            v-if="hasProfiles"
            class="flex flex-wrap items-center justify-center gap-1 text-rui-text-secondary"
          >
            <span>{{ t('create_account.have_account.description') }}</span>
            <RuiButton
              color="primary"
              variant="text"
              type="button"
              data-testid="login"
              :disabled="loading"
              @click="emit('cancel')"
            >
              {{ t('create_account.have_account.log_in') }}
            </RuiButton>
          </div>
        </div>
        <CreateAccountPremium
          v-else-if="screen === 'premium'"
          v-model:form="modelPremiumSetupForm"
          :loading="loading"
          @back="prevStep()"
          @next="nextStep()"
        />
        <CreateAccountCredentials
          v-else-if="screen === 'profile'"
          v-model:form="modelCredentialsForm"
          v-model:password-confirm="modelPasswordConfirm"
          v-model:user-prompted="modelUserPrompted"
          :loading="loading"
          :mode="mode ?? 'create'"
          @back="prevStep()"
          @next="nextStep()"
        />
        <CreateAccountPreferences
          v-else-if="screen === 'preferences'"
          v-model:main-currency="modelMainCurrency"
          v-model:submit-usage-analytics="modelSubmitUsageAnalytics"
          v-model:premium-enabled="modelPremiumEnabled"
          v-model:premium-form="modelPremiumSetupForm"
          v-model:premium-should-sync="modelPremiumShouldSync"
          :loading="loading"
          :error="error"
          @back="prevStep()"
          @confirm="confirm()"
        />
        <CreateAccountRestoreSummary
          v-else-if="screen === 'summary'"
          :api-key="modelPremiumSetupForm.apiKey"
          :username="modelCredentialsForm.username"
          :loading="loading"
          :error="error"
          @back="prevStep()"
          @go-to="goTo($event)"
          @confirm="confirm()"
        />
      </div>
    </Transition>
  </div>
</template>
