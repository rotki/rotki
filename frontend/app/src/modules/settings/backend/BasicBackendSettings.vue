<script setup lang="ts">
import type { BackendOptions } from '@shared/ipc';
import type { LogLevel } from '@shared/log-level';
import { RuiButton, RuiIcon, RuiTextField } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import LogLevelInput from '@/modules/settings/backend/LogLevelInput.vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

/* Not `dataDirectory`: vue-tsc reads `v-model:data-directory` as a `data-*` attribute and drops it. */
const dataDirectory = defineModel<string>('userDataDirectory', { required: true });
const logDirectory = defineModel<string>('userLogDirectory', { required: true });
const logLevel = defineModel<LogLevel>('logLevel', { required: true });

const { fileConfig } = defineProps<{
  fileConfig: Partial<BackendOptions>;
}>();

const { t } = useI18n({ useScope: 'global' });

const { openDirectory } = useInterop();

const selecting = ref<boolean>(false);

async function selectDataDirectory() {
  if (get(selecting))
    return;

  set(selecting, true);
  try {
    const title = t('backend_settings.data_directory.select');
    const directory = await openDirectory(title);
    if (directory)
      set(dataDirectory, directory);
  }
  finally {
    set(selecting, false);
  }
}

async function selectLogsDirectory() {
  if (get(selecting))
    return;

  set(selecting, true);
  try {
    const directory = await openDirectory(t('backend_settings.log_directory.select'));
    if (directory)
      set(logDirectory, directory);
  }
  finally {
    set(selecting, false);
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiTextField
      v-model="dataDirectory"
      data-testid="user-data-directory-input"
      class="pt-2"
      color="primary"
      :disabled="!!fileConfig.dataDirectory || !dataDirectory"
      :hint="
        !!fileConfig.dataDirectory
          ? t('backend_settings.config_file_disabled')
          : t('backend_settings.settings.data_directory.hint')
      "
      :label="t('backend_settings.settings.data_directory.label')"
      readonly
      @click="selectDataDirectory()"
    >
      <template #append>
        <RuiButton
          variant="text"
          icon
          :disabled="!dataDirectory"
          @click="selectDataDirectory()"
        >
          <RuiIcon name="lu-folder" />
        </RuiButton>
      </template>
    </RuiTextField>
    <RuiTextField
      v-model="logDirectory"
      data-testid="user-log-directory-input"
      :disabled="!!fileConfig.logDirectory"
      :hint="!!fileConfig.logDirectory ? t('backend_settings.config_file_disabled') : undefined"
      color="primary"
      :label="t('backend_settings.settings.log_directory.label')"
      readonly
      @click="selectLogsDirectory()"
    >
      <template #append>
        <RuiButton
          variant="text"
          icon
          @click="selectLogsDirectory()"
        >
          <RuiIcon name="lu-folder" />
        </RuiButton>
      </template>
    </RuiTextField>

    <LogLevelInput
      v-model="logLevel"
      :disabled="!!fileConfig.loglevel"
      :error-messages="!!fileConfig.loglevel ? t('backend_settings.config_file_disabled') : undefined"
    />
  </div>
</template>
