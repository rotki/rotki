<script lang="ts" setup>
import type { CreateAccountPayload, LoginCredentials, PremiumSetup } from '@/types/login';
import { externalLinks } from '@shared/external-links';
import CreateAccountSubmitAnalytics
  from '@/components/account-management/create-account/analytics/CreateAccountSubmitAnalytics.vue';
import CreateAccountCredentials
  from '@/components/account-management/create-account/credentials/CreateAccountCredentials.vue';
import CreateAccountIntroduction
  from '@/components/account-management/create-account/introduction/CreateAccountIntroduction.vue';
import CreateAccountPremium from '@/components/account-management/create-account/premium/CreateAccountPremium.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';

const step = defineModel<number>('step', { required: true });

const props = withDefaults(
  defineProps<{
    loading: boolean;
    error?: string;
  }>(),
  { error: '' },
);

const emit = defineEmits<{
  'cancel': [];
  'confirm': [payload: CreateAccountPayload];
  'clear-error': [];
}>();

const { error } = toRefs(props);

const cancel = (): void => emit('cancel');
const errorClear = (): void => emit('clear-error');

function prevStep(): void {
  set(step, get(step) - 1);
  if (get(error))
    errorClear();
}

function nextStep(): void {
  set(step, get(step) + 1);
}

const { t } = useI18n({ useScope: 'global' });

const parsedError = computed<{ hasLink: boolean; parts: string[] }>(() => {
  const errorMessage = get(error);
  const linkPlaceholder = '_DEVICE_LIMIT_LINK_';

  if (!errorMessage || !errorMessage.includes(linkPlaceholder)) {
    return {
      hasLink: false,
      parts: [errorMessage],
    };
  }

  return {
    hasLink: true,
    parts: errorMessage.split(linkPlaceholder),
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
            {{ t('create_account.title') }}
          </h4>
          <div class="w-full">
            <RuiTabItems
              class="!overflow-visible"
              :model-value="step - 1"
            >
              <RuiTabItem>
                <CreateAccountIntroduction @next="nextStep()" />
              </RuiTabItem>
              <RuiTabItem>
                <CreateAccountPremium
                  v-model:premium-enabled="premiumEnabled"
                  v-model:form="premiumSetupForm"
                  :loading="loading"
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
                  :sync-database="premiumSetupForm.syncDatabase"
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
                      {{ t('common.actions.continue') }}
                    </RuiButton>
                  </div>
                </div>
              </RuiTabItem>
            </RuiTabItems>
          </div>
          <div class="items-center flex justify-stretch py-6 text-rui-text-secondary">
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
