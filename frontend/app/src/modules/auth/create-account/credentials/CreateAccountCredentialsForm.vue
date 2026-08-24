<script setup lang="ts">
import type { ZodType } from 'zod';
import type { LoginCredentials } from '@/modules/auth/login';
import {
  type CredentialsFormState,
  credentialsSchema,
} from '@/modules/auth/create-account/credentials/credentials-form';
import { useModelForm } from '@/modules/core/form/use-model-form';

const form = defineModel<LoginCredentials>('form', { required: true });
const valid = defineModel<boolean>('valid', { required: true });
const passwordConfirm = defineModel<string>('passwordConfirm', { required: true });
const userPrompted = defineModel<boolean>('userPrompted', { required: true });

const { loading = false } = defineProps<{
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * The validated state is spread across three models, because only two of its four fields are
 * credentials. This presents them as the one object the form validates and writes each half back
 * where it came from. The round trip has to be lossless, or the core reads its own write back as an
 * edit nobody made.
 */
const bridgedState = computed<CredentialsFormState>({
  get: () => ({
    password: get(form).password,
    passwordConfirm: get(passwordConfirm),
    userPrompted: get(userPrompted),
    username: get(form).username,
  }),
  set: (next: CredentialsFormState) => {
    set(form, { ...get(form), password: next.password, username: next.username });
    set(passwordConfirm, next.passwordConfirm);
    set(userPrompted, next.userPrompted);
  },
});

const schema = computed<ZodType>(() => credentialsSchema({
  confirmationMismatch: t('create_account.credentials.validation.password_confirmation_mismatch'),
  emptyConfirmation: t('create_account.credentials.validation.non_empty_password_confirmation'),
  emptyPassword: t('create_account.credentials.validation.non_empty_password'),
  invalidUsername: t('create_account.credentials.validation.valid_username'),
  prompt: t('create_account.credentials.validation.check_prompt'),
  requiredUsername: t('create_account.credentials.validation.non_empty_username'),
}));

const { errors, state, touch, valid: parses } = useModelForm<CredentialsFormState>({
  model: bridgedState,
  schema,
});

// Immediate, so the wizard step starts with a real answer. A plain watch would leave `valid` at its
// default and Continue would gate on a stale value.
syncRefs(parses, valid);
</script>

<template>
  <div>
    <div class="space-y-3">
      <RuiTextField
        v-model="state.username"
        dense
        color="primary"
        variant="outlined"
        autofocus
        data-testid="create-account__fields__username"
        :label="t('create_account.credentials.label_username')"
        :error-messages="errors('username')"
        :disabled="loading"
        @update:model-value="touch('username')"
      />
      <RuiRevealableTextField
        v-model="state.password"
        dense
        color="primary"
        variant="outlined"
        data-testid="create-account__fields__password"
        :label="t('create_account.credentials.label_password')"
        :error-messages="errors('password')"
        :disabled="loading"
        @update:model-value="touch('password')"
      />
      <RuiRevealableTextField
        v-model="state.passwordConfirm"
        dense
        color="primary"
        variant="outlined"
        data-testid="create-account__fields__password-repeat"
        :label="t('create_account.credentials.label_password_repeat')"
        :error-messages="errors('passwordConfirm')"
        :disabled="loading"
        @update:model-value="touch('passwordConfirm')"
      />
    </div>
    <RuiCheckbox
      v-model="state.userPrompted"
      data-testid="create-account__boxes__user-prompted"
      :disabled="loading"
      color="primary"
      :error-messages="errors('userPrompted')"
      @update:model-value="touch('userPrompted')"
    >
      {{ t('create_account.credentials.label_password_backup_reminder') }}
    </RuiCheckbox>
  </div>
</template>
