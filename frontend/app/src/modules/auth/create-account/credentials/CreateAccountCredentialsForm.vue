<script setup lang="ts">
import type { ZodType } from 'zod';
import type { LoginCredentials } from '@/modules/auth/login';
import {
  type CredentialsFormState,
  credentialsSchema,
} from '@/modules/auth/create-account/credentials/credentials-form';
import PasswordStrengthMeter from '@/modules/auth/create-account/credentials/PasswordStrengthMeter.vue';
import { useFormErrorFocus } from '@/modules/core/common/use-form-error-focus';
import { useModelForm } from '@/modules/core/form/use-model-form';

const form = defineModel<LoginCredentials>('form', { required: true });
const passwordConfirm = defineModel<string>('passwordConfirm', { required: true });
const userPrompted = defineModel<boolean>('userPrompted', { required: true });

const { loading = false } = defineProps<{
  loading?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const root = useTemplateRef<HTMLElement>('root');

const { focusFirstError } = useFormErrorFocus(root);

/** While the password is shown the user can read it, so the repeat field is hidden and not checked. */
const revealed = ref<boolean>(false);

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
}, !get(revealed)));

const { errorCount, errors, state, touch, validate: revealErrors } = useModelForm<CredentialsFormState>({
  model: bridgedState,
  schema,
});

const passwordType = computed<'password' | 'text'>(() => (get(revealed) ? 'text' : 'password'));

const revealLabel = computed<string>(() => (get(revealed)
  ? t('create_account.credentials.hide_password')
  : t('create_account.credentials.show_password')));

/**
 * Reveals every error and moves focus to the first field holding one.
 *
 * @returns whether the step can be left
 */
async function validate(): Promise<boolean> {
  if (revealErrors())
    return true;
  await focusFirstError();
  return false;
}

defineExpose({ errorCount, validate });
</script>

<template>
  <div
    ref="root"
    class="flex flex-col gap-1"
  >
    <RuiTextField
      v-model="state.username"
      color="primary"
      autofocus
      autocomplete="username"
      data-testid="create-account-username"
      :label="t('create_account.credentials.label_username')"
      :error-messages="errors('username')"
      :disabled="loading"
      @update:model-value="touch('username')"
    />
    <RuiTextField
      v-model="state.password"
      color="primary"
      autocomplete="new-password"
      data-testid="create-account-password"
      :type="passwordType"
      :label="t('create_account.credentials.label_password')"
      :error-messages="errors('password')"
      :disabled="loading"
      details="auto"
      @update:model-value="touch('password')"
    >
      <template #append>
        <RuiButton
          variant="text"
          type="button"
          icon
          class="-mr-1 p-1!"
          data-testid="create-account-password-reveal"
          :aria-label="revealLabel"
          :aria-pressed="revealed"
          :disabled="loading"
          @click="revealed = !revealed"
        >
          <RuiIcon
            size="16"
            class="text-rui-text-secondary"
            :name="revealed ? 'lu-eye' : 'lu-eye-off'"
          />
        </RuiButton>
      </template>
    </RuiTextField>
    <PasswordStrengthMeter
      class="mb-4"
      :password="state.password"
    />
    <RuiTextField
      v-if="!revealed"
      v-model="state.passwordConfirm"
      color="primary"
      type="password"
      autocomplete="new-password"
      data-testid="create-account-password-repeat"
      :label="t('create_account.credentials.label_password_repeat')"
      :error-messages="errors('passwordConfirm')"
      :disabled="loading"
      @update:model-value="touch('passwordConfirm')"
    />
    <div
      class="rounded-md border p-3 transition-colors"
      :class="errors('userPrompted').length > 0
        ? 'border-rui-error bg-rui-error/10'
        : 'border-rui-warning/50 bg-rui-warning/10'"
      data-testid="create-account-password-callout"
    >
      <RuiCheckbox
        v-model="state.userPrompted"
        data-testid="create-account-user-prompted"
        :disabled="loading"
        color="primary"
        :error-messages="errors('userPrompted')"
        details="auto"
        @update:model-value="touch('userPrompted')"
      >
        {{ t('create_account.credentials.label_password_backup_reminder') }}
      </RuiCheckbox>
    </div>
  </div>
</template>
