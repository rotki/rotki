<script setup lang="ts">
import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';
import { useForm } from '@/modules/core/form/use-form';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface PasswordConfirmationState {
  password: string;
}

const display = defineModel<boolean>({ required: true });

const {
  errorMessage = '',
  username,
} = defineProps<{
  username: string;
  errorMessage?: string;
}>();

const emit = defineEmits<{
  confirm: [password: string];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getPassword } = useInterop();

const storedPassword = ref<string>('');

const schema = computed<ZodType>(() => z.object({
  password: requiredField(t('password_confirmation_dialog.validation.non_empty_password')),
}));

const form = useForm<PasswordConfirmationState, PasswordConfirmationState>({
  initial: (): PasswordConfirmationState => ({ password: '' }),
  schema,
  // The dialog reports the password upwards and nothing else; the caller owns the attempt.
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): PasswordConfirmationState => ({ ...state }),
});

/**
 * The rejection the caller is holding, shown on the field it belongs to. The core keys it apart
 * from the schema so the two now show together, where the old computed replaced one with the other.
 * It is re-applied on open because `reset()` drops it along with everything else.
 */
function showServerError(): void {
  form.setServerErrors(errorMessage ? { password: [errorMessage] } : {});
}

function confirmPassword(): void {
  if (!form.validate())
    return;

  emit('confirm', form.state.password);
}

watchImmediate(() => errorMessage, () => {
  showServerError();
});

watchImmediate(display, async (isDisplayed) => {
  if (isDisplayed) {
    form.reset();
    showServerError();
    // Fetch stored password when dialog opens
    if (username)
      set(storedPassword, await getPassword(username));
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
          v-model="form.state.password"
          variant="outlined"
          color="primary"
          :label="t('password_confirmation_dialog.password_label')"
          :error-messages="form.errors('password')"
          type="password"
          autofocus
          data-testid="password-confirmation-input"
          @update:model-value="form.touch('password')"
          @keydown.enter="confirmPassword()"
        />
      </div>

      <template #footer>
        <div class="w-full flex gap-2 justify-between items-center">
          <div
            v-if="storedPassword"
            class="text-sm text-rui-text-secondary font-mono"
          >
            {{ t('password_confirmation_dialog.hint_prefix') }} {{ storedPassword.length }}
          </div>
          <div v-else />
          <RuiButton
            color="primary"
            data-testid="password-confirmation-confirm"
            @click="confirmPassword()"
          >
            {{ t('common.actions.confirm') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
