<script lang="ts" setup>
import {
  type CreateAccountPayload,
  type LoginCredentials,
  type PremiumSetup
} from '@/types/login';

const props = withDefaults(
  defineProps<{
    step: number;
    loading: boolean;
    error?: string;
  }>(),
  { error: '' }
);

const emit = defineEmits<{
  (e: 'cancel'): void;
  (e: 'update:step', step: number): void;
  (e: 'confirm', payload: CreateAccountPayload): void;
  (e: 'error:clear'): void;
}>();

const { step, error } = toRefs(props);

const setStep = (newStep: number) => {
  emit('update:step', newStep);
};

const cancel = () => emit('cancel');
const errorClear = () => emit('error:clear');

const prevStep = () => {
  setStep(get(step) - 1);
  if (get(error)) {
    errorClear();
  }
};

const nextStep = () => {
  setStep(get(step) + 1);
};

const css = useCssModule();
const { t } = useI18n();

const premiumEnabled: Ref<boolean> = ref(false);
const premiumSetupForm: Ref<PremiumSetup> = ref({
  apiKey: '',
  apiSecret: '',
  syncDatabase: false
});

const credentialsForm: Ref<LoginCredentials> = ref({
  username: '',
  password: ''
});
const passwordConfirm: Ref<string> = ref('');
const userPrompted: Ref<boolean> = ref(false);
const submitUsageAnalytics: Ref<boolean> = ref(true);

const confirm = () => {
  const payload: CreateAccountPayload = {
    credentials: get(credentialsForm),
    initialSettings: {
      submitUsageAnalytics: get(submitUsageAnalytics)
    }
  };

  if (get(premiumEnabled)) {
    payload.premiumSetup = get(premiumSetupForm);
  }

  emit('confirm', payload);
};
</script>

<template>
  <Transition
    appear
    enter-class="translate-y-5 opacity-0"
    enter-to-class="translate-y-0 opacity-1"
    enter-active-class="transform duration-300"
    leave-class="-translate-y-0 opacity-1"
    leave-to-class="-translate-y-5 opacity-0"
    leave-active-class="transform duration-100"
  >
    <div :class="css.register">
      <div :class="css.register__wrapper">
        <div class="flex flex-col items-center">
          <RuiLogo />
          <h4 class="text-h4 mb-3 mt-8">
            {{ t('create_account.title') }}
          </h4>
          <div class="w-full">
            <RuiTabItems :value="step - 1">
              <template #default>
                <RuiTabItem>
                  <CreateAccountIntroduction @next="nextStep()" />
                </RuiTabItem>
                <RuiTabItem>
                  <CreateAccountPremium
                    :loading="loading"
                    :premium-enabled.sync="premiumEnabled"
                    :form.sync="premiumSetupForm"
                    @back="prevStep()"
                    @next="nextStep()"
                  />
                </RuiTabItem>
                <RuiTabItem>
                  <CreateAccountCredentials
                    :loading="loading"
                    :sync-database="premiumSetupForm.syncDatabase"
                    :form.sync="credentialsForm"
                    :password-confirm.sync="passwordConfirm"
                    :user-prompted.sync="userPrompted"
                    @back="prevStep()"
                    @next="nextStep()"
                  />
                </RuiTabItem>
                <RuiTabItem>
                  <div class="space-y-8">
                    <CreateAccountSubmitAnalytics
                      :loading="loading"
                      :submit-usage-analytics.sync="submitUsageAnalytics"
                    />
                    <RuiAlert v-if="error" type="error">
                      {{ error }}
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
              </template>
            </RuiTabItems>
          </div>
          <div :class="css.register__actions__footer">
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

<style module lang="scss">
.register {
  &__wrapper {
    @apply max-w-[22.5rem] mx-auto;
  }

  &__actions {
    &__footer {
      @apply items-center justify-center flex justify-stretch py-6 text-rui-text-secondary;
    }
  }
}
</style>
