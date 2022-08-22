<template>
  <card>
    <template #title>{{ $t('change_password.title') }}</template>

    <v-form ref="form">
      <v-alert
        v-if="premiumSync"
        data-cy="premium-warning"
        type="warning"
        prominent
        outlined
        v-text="$t('change_password.sync_warning')"
      />
      <revealable-input
        v-model="currentPassword"
        class="user-security-settings__fields__current-password"
        :label="$t('change_password.labels.password')"
        :error-messages="v$.currentPassword.$errors.map(e => e.$message)"
        outlined
      />
      <revealable-input
        v-model="newPassword"
        class="user-security-settings__fields__new-password"
        :label="$t('change_password.labels.new_password')"
        :error-messages="v$.newPassword.$errors.map(e => e.$message)"
        outlined
      />
      <revealable-input
        v-model="newPasswordConfirm"
        class="user-security-settings__fields__new-password-confirm"
        :label="$t('change_password.labels.confirm_password')"
        prepend-icon="mdi-repeat"
        :error-messages="v$.newPasswordConfirm.$errors.map(e => e.$message)"
        outlined
      />
    </v-form>

    <template #buttons>
      <v-btn
        depressed
        class="user-security-settings__buttons__change-password"
        color="primary"
        :loading="loading"
        :disabled="v$.$invalid || loading"
        @click="change()"
        v-text="$t('change_password.button')"
      />
    </template>
  </card>
</template>
<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, sameAs } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { ref } from 'vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import i18n from '@/i18n';
import { useSessionStore } from '@/store/session';
import { usePremiumStore } from '@/store/session/premium';

type Form = {
  reset: () => boolean;
};

const currentPassword = ref('');
const newPassword = ref('');
const newPasswordConfirm = ref('');
const loading = ref(false);
const form = ref();

const rules = {
  currentPassword: {
    required: helpers.withMessage(
      i18n.t('change_password.validation.empty_password').toString(),
      required
    )
  },
  newPassword: {
    required: helpers.withMessage(
      i18n.t('change_password.validation.empty_password').toString(),
      required
    )
  },
  newPasswordConfirm: {
    required: helpers.withMessage(
      i18n.t('change_password.validation.empty_confirmation').toString(),
      required
    ),
    same: helpers.withMessage(
      i18n.t('change_password.validation.password_mismatch').toString(),
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
