<script setup lang="ts">
import type { ZodType } from 'zod';
import { startPromise } from '@shared/utils';
import { Constraints } from '@/modules/core/common/constraints';
import { useForm } from '@/modules/core/form/use-form';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import {
  type PasswordConfirmationFormState,
  passwordConfirmationSchema,
  toIntervalDays,
  toIntervalSeconds,
} from '@/modules/settings/data-security/password-confirmation-form';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';

interface PasswordConfirmationPayload {
  enablePasswordConfirmation: boolean;
  passwordConfirmationInterval: number;
}

const SAVE_DEBOUNCE = 800;

const { t } = useI18n({ useScope: 'global' });

const { updateFrontendSetting } = useSettingsOperations();
const { setSuccess, success } = useClearableMessages();
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
    setSuccess(t('password_confirmation_setting.saved'), true);
    return { success: true };
  },
  transform: (state): PasswordConfirmationPayload => ({
    enablePasswordConfirmation: get(enabled),
    passwordConfirmationInterval: toIntervalSeconds(state.intervalDays),
  }),
});

const invalid = computed<boolean>(() => !get(form.valid));

const hasChanged = computed<boolean>(() => {
  const currentDays = Number.parseFloat(form.state.intervalDays);
  const storedDays = get(passwordConfirmationInterval) / Constraints.SECONDS_PER_DAY;
  return currentDays !== storedDays || get(enabled) !== get(enablePasswordConfirmation);
});

/** Writes the toggle and interval, as every other setting does on change, once they differ from what is stored and are valid. */
async function save(): Promise<void> {
  if (!get(hasChanged) || get(invalid))
    return;
  await form.submit();
}

const scheduleSave = useDebounceFn(save, SAVE_DEBOUNCE);

function onIntervalInput(): void {
  form.touch('intervalDays');
  startPromise(scheduleSave());
}

/**
 * Applies the toggle, asking first when it is being turned off.
 *
 * @remarks
 * Turning the confirmation off weakens the account, so unlike turning it on it goes through a
 * warning rather than being applied directly.
 */
function handleToggleChange(value: boolean): void {
  if (!value) {
    set(showDisableWarning, true);
    return;
  }
  set(enabled, value);
  startPromise(save());
}

function confirmDisable(): void {
  set(enabled, false);
  set(showDisableWarning, false);
  startPromise(save());
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
    data-testid="password-confirmation-setting"
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
      data-testid="enable-password-confirmation-toggle"
      :label="t('password_confirmation_setting.enable_label')"
      @update:model-value="handleToggleChange($event)"
    />

    <RuiTextField
      v-model="form.state.intervalDays"
      color="primary"
      type="number"
      step="1"
      :min="Constraints.MIN_PASSWORD_CONFIRMATION_DAYS"
      :max="Constraints.MAX_PASSWORD_CONFIRMATION_DAYS"
      :label="t('password_confirmation_setting.label')"
      :hint="t('password_confirmation_setting.hint')"
      :success-messages="success"
      :error-messages="form.errors('intervalDays')"
      :disabled="!enabled"
      data-testid="password-confirmation-interval-input"
      @update:model-value="onIntervalInput()"
    />

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
