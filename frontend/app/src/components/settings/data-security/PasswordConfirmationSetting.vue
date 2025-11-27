<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { Constraints } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { toMessages } from '@/utils/validation';

const { t } = useI18n({ useScope: 'global' });

const frontendSettingsStore = useFrontendSettingsStore();
const { updateSetting } = frontendSettingsStore;
const { enablePasswordConfirmation, passwordConfirmationInterval } = storeToRefs(frontendSettingsStore);

const passwordConfirmationIntervalDays = ref<string>('7');
const enabled = ref<boolean>(true);
const loading = ref<boolean>(false);
const showDisableWarning = ref<boolean>(false);

const rules = {
  passwordConfirmationIntervalDays: {
    between: helpers.withMessage(
      t('password_confirmation_setting.validation.range'),
      between(Constraints.MIN_PASSWORD_CONFIRMATION_DAYS, Constraints.MAX_PASSWORD_CONFIRMATION_DAYS),
    ),
    required: helpers.withMessage(
      t('password_confirmation_setting.validation.range'),
      required,
    ),
  },
};

const v$ = useVuelidate(rules, { passwordConfirmationIntervalDays }, { $autoDirty: true });

watchImmediate([passwordConfirmationInterval, enablePasswordConfirmation], ([intervalInSeconds, enable]) => {
  set(passwordConfirmationIntervalDays, String(intervalInSeconds / Constraints.SECONDS_PER_DAY));
  set(enabled, enable);
});

const hasChanged = computed<boolean>(() => {
  const currentDays = Number.parseFloat(get(passwordConfirmationIntervalDays));
  const storedDays = get(passwordConfirmationInterval) / Constraints.SECONDS_PER_DAY;
  const intervalChanged = currentDays !== storedDays;
  const enabledChanged = get(enabled) !== get(enablePasswordConfirmation);
  return intervalChanged || enabledChanged;
});

function handleToggleChange(value: boolean): void {
  if (!value) {
    // User is trying to disable password confirmation, show warning
    set(showDisableWarning, true);
  }
  else {
    set(enabled, value);
  }
}

function confirmDisable(): void {
  set(enabled, false);
  set(showDisableWarning, false);
}

function cancelDisable(): void {
  set(showDisableWarning, false);
}

async function saveSettings(): Promise<void> {
  const isEnabled = get(enabled);
  if (isEnabled && !await get(v$).$validate())
    return;

  set(loading, true);
  const days = Number.parseFloat(get(passwordConfirmationIntervalDays));
  const intervalInSeconds = Math.round(days * Constraints.SECONDS_PER_DAY);
  await updateSetting({
    enablePasswordConfirmation: isEnabled,
    passwordConfirmationInterval: intervalInSeconds,
  });
  set(loading, false);
}
</script>

<template>
  <SettingsItem data-cy="password-confirmation-setting">
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
      v-model="passwordConfirmationIntervalDays"
      variant="outlined"
      color="primary"
      type="number"
      step="1"
      :min="Constraints.MIN_PASSWORD_CONFIRMATION_DAYS"
      :max="Constraints.MAX_PASSWORD_CONFIRMATION_DAYS"
      :label="t('password_confirmation_setting.label')"
      :hint="t('password_confirmation_setting.hint')"
      :error-messages="toMessages(v$.passwordConfirmationIntervalDays)"
      :disabled="!enabled"
      data-cy="password-confirmation-interval-input"
    />

    <div class="flex justify-end mt-4">
      <RuiButton
        data-cy="save-password-confirmation-settings"
        color="primary"
        :loading="loading"
        :disabled="loading || !hasChanged || (enabled && v$.$invalid)"
        @click="saveSettings()"
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
