<script setup lang="ts">
import type { LoginCredentials } from '@/types/login';
import useVuelidate from '@vuelidate/core';
import { helpers, required, sameAs } from '@vuelidate/validators';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const form = defineModel<LoginCredentials>('form', { required: true });
const valid = defineModel<boolean>('valid', { required: true });
const passwordConfirm = defineModel<string>('passwordConfirm', { required: true });
const userPrompted = defineModel<boolean>('userPrompted', { required: true });

withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const { t } = useI18n({ useScope: 'global' });

const username = useRefPropVModel(form, 'username');
const password = useRefPropVModel(form, 'password');

const rules = {
  password: {
    required: helpers.withMessage(t('create_account.credentials.validation.non_empty_password'), required),
  },
  passwordConfirm: {
    isMatch: helpers.withMessage(
      t('create_account.credentials.validation.password_confirmation_mismatch'),
      sameAs(computed<string>(() => get(form).password)),
    ),
    required: helpers.withMessage(t('create_account.credentials.validation.non_empty_password_confirmation'), required),
  },
  username: {
    isValidUsername: helpers.withMessage(
      t('create_account.credentials.validation.valid_username'),
      (v: string): boolean => !!(v && /^[\w.-]+$/.test(v)),
    ),
    required: helpers.withMessage(t('create_account.credentials.validation.non_empty_username'), required),
  },
  userPrompted: {
    required: helpers.withMessage(t('create_account.credentials.validation.check_prompt'), sameAs(true)),
  },
};

const v$ = useVuelidate(
  rules,
  {
    password,
    passwordConfirm,
    username,
    userPrompted,
  },
  {
    $autoDirty: true,
  },
);

watchImmediate(v$, ({ $invalid }) => {
  set(valid, !$invalid);
});
</script>

<template>
  <div>
    <div class="space-y-3">
      <RuiTextField
        v-model="username"
        dense
        color="primary"
        variant="outlined"
        autofocus
        data-cy="create-account__fields__username"
        :label="t('create_account.credentials.label_username')"
        :error-messages="toMessages(v$.username)"
        :disabled="loading"
      />
      <RuiRevealableTextField
        v-model="password"
        dense
        color="primary"
        variant="outlined"
        data-cy="create-account__fields__password"
        :label="t('create_account.credentials.label_password')"
        :error-messages="toMessages(v$.password)"
        :disabled="loading"
      />
      <RuiRevealableTextField
        v-model="passwordConfirm"
        dense
        color="primary"
        variant="outlined"
        data-cy="create-account__fields__password-repeat"
        :label="t('create_account.credentials.label_password_repeat')"
        :error-messages="toMessages(v$.passwordConfirm)"
        :disabled="loading"
      />
    </div>
    <RuiCheckbox
      v-model="userPrompted"
      data-cy="create-account__boxes__user-prompted"
      :disabled="loading"
      color="primary"
      :error-messages="toMessages(v$.userPrompted)"
    >
      {{ t('create_account.credentials.label_password_backup_reminder') }}
    </RuiCheckbox>
  </div>
</template>
