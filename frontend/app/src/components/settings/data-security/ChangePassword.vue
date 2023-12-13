<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, sameAs } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

const currentPassword = ref('');
const newPassword = ref('');
const newPasswordConfirm = ref('');
const loading = ref(false);

const { t } = useI18n();

const rules = {
  currentPassword: {
    required: helpers.withMessage(
      t('change_password.validation.empty_password'),
      required
    )
  },
  newPassword: {
    required: helpers.withMessage(
      t('change_password.validation.empty_password'),
      required
    )
  },
  newPasswordConfirm: {
    required: helpers.withMessage(
      t('change_password.validation.empty_confirmation'),
      required
    ),
    same: helpers.withMessage(
      t('change_password.validation.password_mismatch'),
      sameAs(newPassword)
    )
  }
};

const v$ = useVuelidate(
  rules,
  { currentPassword, newPassword, newPasswordConfirm },
  { $autoDirty: true }
);

const { premiumSync } = storeToRefs(usePremiumStore());
const { changePassword } = useSessionStore();

const reset = () => {
  get(v$).$reset();
};

const change = async () => {
  set(loading, true);
  const result = await changePassword({
    currentPassword: get(currentPassword),
    newPassword: get(newPassword)
  });
  set(loading, false);

  if (result.success) {
    reset();
  }
};
</script>

<template>
  <RuiCard>
    <template #header>{{ t('change_password.title') }}</template>

    <form>
      <RuiAlert
        v-if="premiumSync"
        class="mb-4"
        data-cy="premium-warning"
        type="warning"
      >
        {{ t('change_password.sync_warning') }}
      </RuiAlert>
      <RuiRevealableTextField
        v-model="currentPassword"
        color="primary"
        class="user-security-settings__fields__current-password"
        :label="t('change_password.labels.password')"
        :error-messages="toMessages(v$.currentPassword)"
        variant="outlined"
      />
      <RuiRevealableTextField
        v-model="newPassword"
        color="primary"
        class="user-security-settings__fields__new-password"
        :label="t('change_password.labels.new_password')"
        :error-messages="toMessages(v$.newPassword)"
        variant="outlined"
      />
      <RuiRevealableTextField
        v-model="newPasswordConfirm"
        color="primary"
        class="user-security-settings__fields__new-password-confirm"
        :label="t('change_password.labels.confirm_password')"
        prepend-icon="repeat-2-line"
        :error-messages="toMessages(v$.newPasswordConfirm)"
        variant="outlined"
      />
    </form>

    <template #footer>
      <RuiButton
        class="user-security-settings__buttons__change-password"
        color="primary"
        :loading="loading"
        :disabled="v$.$invalid || loading"
        @click="change()"
      >
        {{ t('change_password.button') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
