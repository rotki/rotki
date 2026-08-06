<script setup lang="ts">
import type { ZodType } from 'zod';
import { Constraints } from '@/modules/core/common/constraints';
import { useForm } from '@/modules/core/form/use-form';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import {
  type PasswordConfirmationFormState,
  passwordConfirmationSchema,
  toIntervalDays,
  toIntervalSeconds,
} from '@/modules/settings/data-security/password-confirmation-form';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

interface PasswordConfirmationPayload {
  enablePasswordConfirmation: boolean;
  passwordConfirmationInterval: number;
}

const { t } = useI18n({ useScope: 'global' });

const { updateFrontendSetting } = useSettingsOperations();
const enablePasswordConfirmation = useSetting('enablePasswordConfirmation');
const passwordConfirmationInterval = useSetting('passwordConfirmationInterval');

const enabled = ref<boolean>(true);
const showDisableWarning = ref<boolean>(false);

const schema = computed<ZodType>(() => passwordConfirmationSchema(
  get(enabled),
  t('password_confirmation_setting.validation.range'),
));

const form = useForm<PasswordConfirmationFormState, PasswordConfirmationPayload>({
  initial: (): PasswordConfirmationFormState => ({ intervalDays: toIntervalDays(get(passwordConfirmationInterval)) }),
  schema,
  submit: async (payload: PasswordConfirmationPayload): Promise<{ success: boolean }> => {
    await updateFrontendSetting(payload);
    return { success: true };
  },
  transform: (state): PasswordConfirmationPayload => ({
    enablePasswordConfirmation: get(enabled),
    passwordConfirmationInterval: toIntervalSeconds(state.intervalDays),
  }),
});

const invalid = computed<boolean>(() => !get(form.valid));

const loading = computed<boolean>(() => get(form.submitting));

const hasChanged = computed<boolean>(() => {
  const currentDays = Number.parseFloat(form.state.intervalDays);
  const storedDays = get(passwordConfirmationInterval) / Constraints.SECONDS_PER_DAY;
  return currentDays !== storedDays || get(enabled) !== get(enablePasswordConfirmation);
});

function handleToggleChange(value: boolean): void {
  // Turning the confirmation off weakens the account, so it is confirmed rather than just applied.
  if (!value)
    set(showDisableWarning, true);
  else
    set(enabled, value);
}

function confirmDisable(): void {
  set(enabled, false);
  set(showDisableWarning, false);
}

function cancelDisable(): void {
  set(showDisableWarning, false);
}

watchImmediate([passwordConfirmationInterval, enablePasswordConfirmation], ([intervalInSeconds, enable]) => {
  form.state.intervalDays = toIntervalDays(intervalInSeconds);
  set(enabled, enable);
});
</script>

<template>
  <SettingsItem
    setting-key="enablePasswordConfirmation"
    data-cy="password-confirmation-setting"
  >
    <template #title>
      {{ t('password_confirmation_setting.title') }}
    </template>

    <template #subtitle>
      {{ t('password_confirmation_setting.subtitle') }}
    </template>

    <RuiSwitch
      :model-value="enabled"
      color="primary"
      data-cy="enable-password-confirmation-toggle"
      :label="t('password_confirmation_setting.enable_label')"
      @update:model-value="handleToggleChange($event)"
    />

    <RuiTextField
      v-model="form.state.intervalDays"
      variant="outlined"
      color="primary"
      type="number"
      step="1"
      :min="Constraints.MIN_PASSWORD_CONFIRMATION_DAYS"
      :max="Constraints.MAX_PASSWORD_CONFIRMATION_DAYS"
      :label="t('password_confirmation_setting.label')"
      :hint="t('password_confirmation_setting.hint')"
      :error-messages="form.errors('intervalDays')"
      :disabled="!enabled"
      data-cy="password-confirmation-interval-input"
      @update:model-value="form.touch('intervalDays')"
    />

    <div class="flex justify-end mt-4">
      <RuiButton
        data-cy="save-password-confirmation-settings"
        color="primary"
        :loading="loading"
        :disabled="loading || !hasChanged || invalid"
        @click="form.submit()"
      >
        {{ t('common.actions.save') }}
      </RuiButton>
    </div>

    <ConfirmDialog
      :display="showDisableWarning"
      :title="t('password_confirmation_setting.disable_warning.title')"
      :message="t('password_confirmation_setting.disable_warning.message')"
      :primary-action="t('password_confirmation_setting.disable_warning.confirm')"
      max-width="600"
      @cancel="cancelDisable()"
      @confirm="confirmDisable()"
    />
  </SettingsItem>
</template>
