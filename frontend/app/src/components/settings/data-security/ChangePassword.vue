<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, sameAs } from '@vuelidate/validators';

interface Form {
  reset: () => boolean;
}

const currentPassword = ref('');
const newPassword = ref('');
const newPasswordConfirm = ref('');
const loading = ref(false);
const form = ref();

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
  const passwordForm = get(form) as Form;
  passwordForm.reset();
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
  <Card>
    <template #title>{{ t('change_password.title') }}</template>

    <VForm ref="form">
      <VAlert
        v-if="premiumSync"
        data-cy="premium-warning"
        type="warning"
        prominent
        outlined
      >
        {{ t('change_password.sync_warning') }}
      </VAlert>
      <RevealableInput
        v-model="currentPassword"
        class="user-security-settings__fields__current-password"
        :label="t('change_password.labels.password')"
        :error-messages="v$.currentPassword.$errors.map(e => e.$message)"
        outlined
      />
      <RevealableInput
        v-model="newPassword"
        class="user-security-settings__fields__new-password"
        :label="t('change_password.labels.new_password')"
        :error-messages="v$.newPassword.$errors.map(e => e.$message)"
        outlined
      />
      <RevealableInput
        v-model="newPasswordConfirm"
        class="user-security-settings__fields__new-password-confirm"
        :label="t('change_password.labels.confirm_password')"
        prepend-icon="mdi-repeat"
        :error-messages="v$.newPasswordConfirm.$errors.map(e => e.$message)"
        outlined
      />
    </VForm>

    <template #buttons>
      <RuiButton
        variant="default"
        class="user-security-settings__buttons__change-password"
        color="primary"
        :loading="loading"
        :disabled="v$.$invalid || loading"
        @click="change()"
      >
        {{ t('change_password.button') }}
      </RuiButton>
    </template>
  </Card>
</template>
