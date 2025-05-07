<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { useChangePassword } from '@/modules/account/use-change-password';
import { usePremiumStore } from '@/store/session/premium';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required, sameAs } from '@vuelidate/validators';

const currentPassword = ref('');
const newPassword = ref('');
const newPasswordConfirm = ref('');
const loading = ref(false);

const { t } = useI18n({ useScope: 'global' });

const rules = {
  currentPassword: {
    required: helpers.withMessage(t('change_password.validation.empty_password'), required),
  },
  newPassword: {
    required: helpers.withMessage(t('change_password.validation.empty_password'), required),
  },
  newPasswordConfirm: {
    required: helpers.withMessage(t('change_password.validation.empty_confirmation'), required),
    same: helpers.withMessage(t('change_password.validation.password_mismatch'), sameAs(newPassword)),
  },
};

const v$ = useVuelidate(rules, { currentPassword, newPassword, newPasswordConfirm }, { $autoDirty: true });

const { premiumSync } = storeToRefs(usePremiumStore());
const { changePassword } = useChangePassword();

function reset() {
  get(v$).$reset();
}

async function change() {
  set(loading, true);
  const result = await changePassword({
    currentPassword: get(currentPassword),
    newPassword: get(newPassword),
  });
  set(loading, false);

  if (result.success)
    reset();
}
</script>

<template>
  <RuiAlert
    v-if="premiumSync"
    class="mt-6"
    data-cy="premium-warning"
    type="warning"
  >
    {{ t('change_password.sync_warning') }}
  </RuiAlert>
  <SettingsItem>
    <template #title>
      {{ t('change_password.title') }}
    </template>

    <template #subtitle>
      {{ t('change_password.subtitle') }}
    </template>

    <form>
      <RuiRevealableTextField
        v-model="currentPassword"
        color="primary"
        data-cy="current-password"
        :label="t('change_password.labels.password')"
        :error-messages="toMessages(v$.currentPassword)"
        variant="outlined"
      />
      <RuiRevealableTextField
        v-model="newPassword"
        color="primary"
        data-cy="new-password"
        :label="t('change_password.labels.new_password')"
        prepend-icon="lu-lock-keyhole"
        :error-messages="toMessages(v$.newPassword)"
        variant="outlined"
      />
      <RuiRevealableTextField
        v-model="newPasswordConfirm"
        color="primary"
        data-cy="confirm-password"
        :label="t('change_password.labels.confirm_password')"
        prepend-icon="lu-repeat"
        :error-messages="toMessages(v$.newPasswordConfirm)"
        variant="outlined"
      />
    </form>

    <div class="flex justify-end">
      <RuiButton
        data-cy="change-password-button"
        color="primary"
        :loading="loading"
        :disabled="v$.$invalid || loading"
        @click="change()"
      >
        {{ t('change_password.button') }}
      </RuiButton>
    </div>
  </SettingsItem>
</template>
