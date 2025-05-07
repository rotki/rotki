<script setup lang="ts">
import type { LoginCredentials } from '@/types/login';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required, sameAs } from '@vuelidate/validators';

const props = withDefaults(
  defineProps<{
    loading?: boolean;
    form: LoginCredentials;
    passwordConfirm: string;
    userPrompted: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'update:form', form: LoginCredentials): void;
  (e: 'update:valid', valid: boolean): void;
  (e: 'update:password-confirm', value: string): void;
  (e: 'update:user-prompted', value: boolean): void;
}>();

const { form, passwordConfirm, userPrompted } = toRefs(props);

function input(newInput: Partial<LoginCredentials>) {
  emit('update:form', {
    ...get(form),
    ...newInput,
  });
}

const { t } = useI18n({ useScope: 'global' });

const rules = {
  password: {
    required: helpers.withMessage(t('create_account.credentials.validation.non_empty_password'), required),
  },
  passwordConfirm: {
    isMatch: helpers.withMessage(
      t('create_account.credentials.validation.password_confirmation_mismatch'),
      sameAs(computed(() => get(form).password)),
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
    password: computed(() => get(form).password),
    passwordConfirm,
    username: computed(() => get(form).username),
    userPrompted,
  },
  {
    $autoDirty: true,
  },
);

watchImmediate(v$, ({ $invalid }) => {
  emit('update:valid', !$invalid);
});

const username = computed({
  get() {
    return get(form).username;
  },
  set(value: string) {
    input({ username: value });
  },
});

const password = computed({
  get() {
    return get(form).password;
  },
  set(value: string) {
    input({ password: value });
  },
});

const passwordConfirmModel = computed({
  get() {
    return get(passwordConfirm);
  },
  set(value: string) {
    emit('update:password-confirm', value);
  },
});

const userPromptedModel = computed({
  get() {
    return get(userPrompted);
  },
  set(value: boolean) {
    emit('update:user-prompted', value);
  },
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
        v-model="passwordConfirmModel"
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
      v-model="userPromptedModel"
      data-cy="create-account__boxes__user-prompted"
      :disabled="loading"
      color="primary"
      :error-messages="toMessages(v$.userPrompted)"
    >
      {{ t('create_account.credentials.label_password_backup_reminder') }}
    </RuiCheckbox>
  </div>
</template>
