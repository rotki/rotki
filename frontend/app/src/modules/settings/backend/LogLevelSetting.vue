<script setup lang="ts">
import type { LogLevel } from '@shared/log-level';
import { setLevel } from '@/modules/core/common/logging/logging';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import LogLevelInput from '@/modules/settings/backend/LogLevelInput.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { saveUserOptions } from '@/modules/shell/app/backend-options';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const { t } = useI18n({ useScope: 'global' });

const { backendSettings, updateBackendConfiguration } = useSettingsApi();
const interop = useInterop();

const logLevel = ref<LogLevel>();
const fileConfigDisabled = ref<boolean>(false);
const loading = ref<boolean>(false);

const { clearAll, error, setError, setSuccess, stop, success, wait } = useClearableMessages();

async function loadConfiguration(): Promise<void> {
  const config = await backendSettings();
  set(logLevel, config.loglevel.value);
  set(fileConfigDisabled, !config.loglevel.isDefault);
}

async function handleUpdate(newValue: LogLevel): Promise<void> {
  stop();
  clearAll();
  set(loading, true);

  try {
    saveUserOptions({ loglevel: newValue });
    await updateBackendConfiguration(newValue);
    setLevel(newValue);
    if (interop.isPackaged) {
      interop.setLogLevel(newValue);
    }
    await wait();
    setSuccess('', true);
  }
  catch (error_: any) {
    await wait();
    setError(error_.message || '', true);
  }
  finally {
    await loadConfiguration();
    set(loading, false);
  }
}

const debounceUpdate = useDebounceFn(handleUpdate, 1500);

function update(newValue: LogLevel): void {
  set(logLevel, newValue);
  clearAll();
  debounceUpdate(newValue);
}

onBeforeMount(async () => {
  await loadConfiguration();
});
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('backend_settings.settings.log_level.label') }}
    </template>
    <template #subtitle>
      {{ t('backend_settings.settings.log_level.hint') }}
    </template>
    <LogLevelInput
      v-if="logLevel"
      :model-value="logLevel"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event)"
    />
  </SettingsItem>
</template>
