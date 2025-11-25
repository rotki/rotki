<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { useInterop } from '@/composables/electron-interop';
import { toMessages } from '@/utils/validation';

const display = defineModel<boolean>({ required: true });

const props = withDefaults(
  defineProps<{
    username: string;
    errorMessage?: string;
  }>(),
  {
    errorMessage: '',
  },
);

const emit = defineEmits<{
  confirm: [password: string];
}>();

const { t } = useI18n({ useScope: 'global' });

const { errorMessage, username } = toRefs(props);
const { getPassword } = useInterop();

const password = ref<string>('');
const storedPassword = ref<string>('');

const rules = {
  password: {
    required: helpers.withMessage(
      t('password_confirmation_dialog.validation.non_empty_password'),
      required,
    ),
  },
};

const v$ = useVuelidate(rules, { password }, { $autoDirty: true });

const passwordErrors = computed<string[]>(() => {
  const errors = toMessages(get(v$).password);
  const externalError = get(errorMessage);
  if (externalError)
    return [externalError];

  return errors;
});

const passwordHint = computed<string>(() => {
  const stored = get(storedPassword);
  if (!stored)
    return '';

  return '*'.repeat(stored.length);
});

async function confirmPassword(): Promise<void> {
  if (!await get(v$).$validate())
    return;

  emit('confirm', get(password));
}

watchImmediate(display, async (isDisplayed) => {
  if (isDisplayed) {
    set(password, '');
    get(v$).$reset();
    // Fetch stored password when dialog opens
    const usernameValue = get(username);
    if (usernameValue)
      set(storedPassword, await getPassword(usernameValue));
  }
});
</script>

<template>
  <RuiDialog
    v-model="display"
    max-width="500"
    persistent
  >
    <RuiCard content-class="!pt-0">
      <template #header>
        {{ t('password_confirmation_dialog.title') }}
      </template>

      <div class="flex flex-col gap-4">
        <i18n-t
          keypath="password_confirmation_dialog.description"
          tag="div"
          class="text-rui-text-secondary"
        >
          <template #username>
            <span class="font-bold font-mono">{{ username }}</span>
          </template>
        </i18n-t>

        <RuiTextField
          v-model="password"
          variant="outlined"
          color="primary"
          :label="t('password_confirmation_dialog.password_label')"
          :error-messages="passwordErrors"
          type="password"
          autofocus
          data-cy="password-confirmation-input"
          @keydown.enter="confirmPassword()"
        />
      </div>

      <template #footer>
        <div class="w-full flex gap-2 justify-between items-center">
          <div
            v-if="passwordHint"
            class="text-sm text-rui-text-secondary font-mono"
          >
            {{ t('password_confirmation_dialog.hint_prefix') }} {{ passwordHint }}
          </div>
          <div v-else />
          <RuiButton
            color="primary"
            data-cy="password-confirmation-confirm"
            @click="confirmPassword()"
          >
            {{ t('common.actions.confirm') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
