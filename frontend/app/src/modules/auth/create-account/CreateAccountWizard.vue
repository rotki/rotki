<script lang="ts" setup>
import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import type { CreateAccountPayload, LoginCredentials, PremiumSetup } from '@/modules/auth/login';
import { externalLinks } from '@shared/external-links';
import CreateAccountSubmitAnalytics
  from '@/modules/auth/create-account/analytics/CreateAccountSubmitAnalytics.vue';
import CreateAccountCredentials
  from '@/modules/auth/create-account/credentials/CreateAccountCredentials.vue';
import CreateAccountIntroduction
  from '@/modules/auth/create-account/introduction/CreateAccountIntroduction.vue';
import CreateAccountPremium from '@/modules/auth/create-account/premium/CreateAccountPremium.vue';
import { useSavedProfiles } from '@/modules/auth/use-saved-profiles';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';

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

const cancel = (): void => emit('cancel');
const errorClear = (): void => emit('clear-error');

function resetPremiumState(): void {
  set(premiumEnabled, false);
  set(premiumSetupForm, { apiKey: '', apiSecret: '', syncDatabase: false });
}

function prevStep(): void {
  const next = get(step) - 1;
  set(step, next);
  if (next === 1) {
    set(mode, undefined);
    resetPremiumState();
  }
  if (error)
    errorClear();
}

function nextStep(): void {
  set(step, get(step) + 1);
}

const { t } = useI18n({ useScope: 'global' });

const { hasProfiles, loadProfiles } = useSavedProfiles();

onBeforeMount(loadProfiles);

const parsedError = computed<{ hasLink: boolean; parts: string[] }>(() => {
  const linkPlaceholder = '_DEVICE_LIMIT_LINK_';

  if (!error || !error.includes(linkPlaceholder)) {
    return {
      hasLink: false,
      parts: [error],
    };
  }

  return {
    hasLink: true,
    parts: error.split(linkPlaceholder),
  };
});

const premiumEnabled = ref<boolean>(false);
const premiumSetupForm = ref<PremiumSetup>({
  apiKey: '',
  apiSecret: '',
  syncDatabase: false,
});

const credentialsForm = ref<LoginCredentials>({
  password: '',
  username: '',
});
const passwordConfirm = ref<string>('');
const userPrompted = ref<boolean>(false);
const submitUsageAnalytics = ref<boolean>(true);

const isRestoreMode = computed<boolean>(() => get(mode) === 'restore');

const wizardTitle = computed<string>(() =>
  get(isRestoreMode) ? t('create_account.title_restore') : t('create_account.title'),
);

const submitLabel = computed<string>(() =>
  get(isRestoreMode) ? t('create_account.actions.restore_account') : t('create_account.actions.create_account'),
);

function selectMode(selected: CreateAccountMode): void {
  set(mode, selected);
  if (selected === 'restore') {
    set(premiumEnabled, true);
    set(premiumSetupForm, { ...get(premiumSetupForm), syncDatabase: true });
  }
  nextStep();
}

function confirm() {
  const payload: CreateAccountPayload = {
    credentials: get(credentialsForm),
    initialSettings: {
      submitUsageAnalytics: get(submitUsageAnalytics),
    },
  };

  if (get(premiumEnabled))
    payload.premiumSetup = get(premiumSetupForm);

  emit('confirm', payload);
}
</script>

<template>
  <Transition
    appear
    enter-from-class="translate-y-5 opacity-0"
    enter-to-class="translate-y-0 opacity-1"
    enter-active-class="transform duration-300"
    leave-from-class="-translate-y-0 opacity-1"
    leave-to-class="-translate-y-5 opacity-0"
    leave-active-class="transform duration-100"
  >
    <div>
      <div class="max-w-[22.5rem] mx-auto">
        <div class="flex flex-col items-center">
          <RotkiLogo unique-key="1b" />
          <h4 class="text-h4 mb-3 mt-8">
            {{ wizardTitle }}
          </h4>
          <div class="w-full">
            <RuiTabItems
              class="!overflow-visible"
              :model-value="step - 1"
            >
              <RuiTabItem>
                <CreateAccountIntroduction @select="selectMode($event)" />
              </RuiTabItem>
              <RuiTabItem>
                <CreateAccountPremium
                  v-model:premium-enabled="premiumEnabled"
                  v-model:form="premiumSetupForm"
                  :loading="loading"
                  :mode="mode ?? 'create'"
                  @back="prevStep()"
                  @next="nextStep()"
                />
              </RuiTabItem>
              <RuiTabItem>
                <CreateAccountCredentials
                  v-model:form="credentialsForm"
                  v-model:password-confirm="passwordConfirm"
                  v-model:user-prompted="userPrompted"
                  :loading="loading"
                  :mode="mode ?? 'create'"
                  @back="prevStep()"
                  @next="nextStep()"
                />
              </RuiTabItem>
              <RuiTabItem>
                <div class="space-y-8">
                  <CreateAccountSubmitAnalytics
                    v-model:submit-usage-analytics="submitUsageAnalytics"
                    :loading="loading"
                  />
                  <RuiAlert
                    v-if="error"
                    type="error"
                  >
                    <template v-if="parsedError.hasLink">
                      {{ parsedError.parts[0] }}
                      <i18n-t keypath="create_account.error.device_limit_link">
                        <template #here>
                          <ExternalLink
                            :url="externalLinks.premiumDevices"
                            custom
                          >
                            {{ t('common.here') }}
                          </ExternalLink>
                        </template>
                      </i18n-t>
                      {{ parsedError.parts[1] }}
                    </template>
                    <template v-else>
                      {{ error }}
                    </template>
                  </RuiAlert>
                  <div class="grid grid-cols-2 gap-4">
                    <RuiButton
                      size="lg"
                      class="w-full"
                      :disabled="loading"
                      @click="prevStep()"
                    >
                      {{ t('common.actions.back') }}
                    </RuiButton>
                    <RuiButton
                      data-cy="create-account__submit-analytics__button__continue"
                      size="lg"
                      class="w-full"
                      :disabled="loading"
                      :loading="loading"
                      color="primary"
                      @click="confirm()"
                    >
                      {{ submitLabel }}
                    </RuiButton>
                  </div>
                </div>
              </RuiTabItem>
            </RuiTabItems>
          </div>
          <div
            v-if="hasProfiles"
            class="flex items-center py-6 text-rui-text-secondary"
          >
            <span>{{ t('create_account.have_account.description') }}</span>
            <RuiButton
              color="primary"
              size="lg"
              variant="text"
              :disabled="loading"
              type="button"
              data-cy="login"
              class="py-1"
              @click="cancel()"
            >
              {{ t('create_account.have_account.log_in') }}
            </RuiButton>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>
