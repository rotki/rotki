<script setup lang="ts">
import type { ZodType } from 'zod';
import { useChangePassword } from '@/modules/auth/use-change-password';
import { useForm } from '@/modules/core/form/use-form';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import {
  type ChangePasswordFormState,
  changePasswordSchema,
  emptyChangePasswordState,
} from '@/modules/settings/data-security/change-password-form';

const { t } = useI18n({ useScope: 'global' });

const { premiumSync } = storeToRefs(usePremiumStore());
const { changePassword } = useChangePassword();

const schema = computed<ZodType>(() => changePasswordSchema({
  emptyConfirmation: t('change_password.validation.empty_confirmation'),
  emptyPassword: t('change_password.validation.empty_password'),
  mismatch: t('change_password.validation.password_mismatch'),
}));

const form = useForm<ChangePasswordFormState, { currentPassword: string; newPassword: string }>({
  initial: emptyChangePasswordState,
  schema,
  submit: async payload => changePassword(payload),
  transform: (state): { currentPassword: string; newPassword: string } => ({
    currentPassword: state.currentPassword,
    newPassword: state.newPassword,
  }),
});

const invalid = computed<boolean>(() => !get(form.valid));

const loading = computed<boolean>(() => get(form.submitting));

async function change(): Promise<void> {
  const result = await form.submit();
  // Only a completed change should wipe what the user typed; a rejected one is worth correcting.
  if (result.outcome === 'success')
    form.reset();
}
</script>

<template>
  <RuiAlert
    v-if="premiumSync"
    class="mt-6"
    data-testid="premium-warning"
    type="warning"
  >
    {{ t('change_password.sync_warning') }}
  </RuiAlert>
  <SettingsItem action-key="changePassword">
    <template #title>
      {{ t('change_password.title') }}
    </template>

    <template #subtitle>
      {{ t('change_password.subtitle') }}
    </template>

    <form
      novalidate
      @submit.stop.prevent="change()"
    >
      <RuiRevealableTextField
        v-model="form.state.currentPassword"
        color="primary"
        data-testid="current-password"
        :label="t('change_password.labels.password')"
        :error-messages="form.errors('currentPassword')"
        variant="outlined"
        @update:model-value="form.touch('currentPassword')"
      />
      <RuiRevealableTextField
        v-model="form.state.newPassword"
        color="primary"
        data-testid="new-password"
        :label="t('change_password.labels.new_password')"
        prepend-icon="lu-lock-keyhole"
        :error-messages="form.errors('newPassword')"
        variant="outlined"
        @update:model-value="form.touch('newPassword')"
      />
      <RuiRevealableTextField
        v-model="form.state.newPasswordConfirm"
        color="primary"
        data-testid="confirm-password"
        :label="t('change_password.labels.confirm_password')"
        prepend-icon="lu-repeat"
        :error-messages="form.errors('newPasswordConfirm')"
        variant="outlined"
        @update:model-value="form.touch('newPasswordConfirm')"
      />
      <div class="flex justify-end">
        <RuiButton
          data-testid="change-password-button"
          color="primary"
          :loading="loading"
          type="submit"
          :disabled="invalid || loading"
        >
          {{ t('change_password.button') }}
        </RuiButton>
      </div>
    </form>
  </SettingsItem>
</template>
