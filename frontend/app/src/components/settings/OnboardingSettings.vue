<script setup lang="ts">
import type { Writeable } from '@rotki/common';
import type { BackendOptions } from '@shared/ipc';
import type { BackendConfiguration } from '@/types/backend';
import useVuelidate from '@vuelidate/core';
import { and, helpers, minValue, numeric, required } from '@vuelidate/validators';
import { isEqual } from 'es-toolkit';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import LogLevelInput from '@/components/settings/backend/LogLevelInput.vue';
import LanguageSetting from '@/components/settings/general/language/LanguageSetting.vue';
import SettingResetButton from '@/components/settings/SettingResetButton.vue';
import { useSettingsApi } from '@/composables/api/settings/settings-api';
import { useBackendManagement } from '@/composables/backend';
import { useInterop } from '@/composables/electron-interop';
import { useConfirmStore } from '@/store/confirm';
import { useMainStore } from '@/store/main';
import { toMessages } from '@/utils/validation';

const emit = defineEmits<{
  dismiss: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { dataDirectory, defaultBackendArguments } = storeToRefs(useMainStore());

const userDataDirectory = ref<string>('');
const userLogDirectory = ref<string>('');
const logFromOtherModules = ref<boolean>(false);
const valid = ref<boolean>(false);

const maxLogSize = ref<string>('0');
const sqliteInstructions = ref<string>('0');
const maxLogFiles = ref<string>('0');

const { backendSettings, updateBackendConfiguration } = useSettingsApi();

const selecting = ref<boolean>(false);
const confirmReset = ref<boolean>(false);
const configuration = ref<BackendConfiguration>();

async function loadConfiguration(): Promise<void> {
  set(configuration, await backendSettings());
}

function parseValue(value?: string) {
  if (!value)
    return 0;

  const parsedValue = Number.parseInt(value);
  return Number.isNaN(parsedValue) ? 0 : parsedValue;
}

function stringifyValue(value?: number) {
  if (!value)
    return '0';

  return value.toString();
}

const {
  applyUserOptions,
  defaultLogDirectory,
  defaultLogLevel,
  fileConfig,
  logLevel,
  options,
  resetOptions,
  saveOptions,
} = useBackendManagement(loaded);

const initialOptions = computed<Partial<BackendOptions>>(() => {
  const config = get(configuration);
  const opts = get(options);
  const defaults = get(defaultBackendArguments);

  return {
    dataDirectory: opts.dataDirectory ?? get(dataDirectory),
    logDirectory: opts.logDirectory ?? get(defaultLogDirectory),
    logFromOtherModules: opts.logFromOtherModules ?? false,
    loglevel: opts.loglevel ?? config?.loglevel?.value ?? get(defaultLogLevel),
    maxLogfilesNum: opts.maxLogfilesNum ?? config?.maxLogfilesNum?.value ?? defaults.maxLogfilesNum,
    maxSizeInMbAllLogs: opts.maxSizeInMbAllLogs ?? config?.maxSizeInMbAllLogs?.value ?? defaults.maxSizeInMbAllLogs,
    sqliteInstructions: opts.sqliteInstructions ?? config?.sqliteInstructions?.value ?? defaults.sqliteInstructions,
  };
});

function loaded() {
  const initial = get(initialOptions);

  set(logLevel, initial.loglevel);
  set(userDataDirectory, initial.dataDirectory);
  set(userLogDirectory, initial.logDirectory);
  set(logFromOtherModules, initial.logFromOtherModules);
  set(maxLogFiles, stringifyValue(initial.maxLogfilesNum));
  set(maxLogSize, stringifyValue(initial.maxSizeInMbAllLogs));
  set(sqliteInstructions, stringifyValue(initial.sqliteInstructions));
}

const isMaxLogFilesDefault = computed(() => {
  const defaults = get(defaultBackendArguments);
  return defaults.maxLogfilesNum === parseValue(get(maxLogFiles));
});

const isMaxSizeDefault = computed(() => {
  const defaults = get(defaultBackendArguments);
  return defaults.maxSizeInMbAllLogs === parseValue(get(maxLogSize));
});

const isSqliteInstructionsDefaults = computed(() => {
  const defaults = get(defaultBackendArguments);
  return defaults.sqliteInstructions === parseValue(get(sqliteInstructions));
});

function resetDefaultArguments(field: 'files' | 'size' | 'instructions') {
  const defaults = get(defaultBackendArguments);
  if (field === 'files')
    set(maxLogFiles, stringifyValue(defaults.maxLogfilesNum));
  else if (field === 'size')
    set(maxLogSize, stringifyValue(defaults.maxSizeInMbAllLogs));
  else if (field === 'instructions')
    set(sqliteInstructions, stringifyValue(defaults.sqliteInstructions));
}

const newUserOptions = computed(() => {
  const initial = get(initialOptions);
  const newOptions: Writeable<Partial<BackendOptions>> = {};

  const level = get(logLevel);
  if (level !== initial.loglevel)
    newOptions.loglevel = level;

  const userData = get(userDataDirectory);
  if (userData !== initial.dataDirectory)
    newOptions.dataDirectory = userData;

  const userLog = get(userLogDirectory);
  if (userLog !== initial.logDirectory)
    newOptions.logDirectory = userLog;

  const logFromOther = get(logFromOtherModules);
  if (logFromOther !== initial.logFromOtherModules)
    newOptions.logFromOtherModules = logFromOther;

  const maxLogFilesParsed = parseValue(get(maxLogFiles));
  if (maxLogFilesParsed !== initial.maxLogfilesNum)
    newOptions.maxLogfilesNum = maxLogFilesParsed;

  const maxLogSizeParsed = parseValue(get(maxLogSize));
  if (maxLogSizeParsed !== initial.maxSizeInMbAllLogs)
    newOptions.maxSizeInMbAllLogs = maxLogSizeParsed;

  const sqliteInstructionsParsed = parseValue(get(sqliteInstructions));
  if (sqliteInstructionsParsed !== initial.sqliteInstructions)
    newOptions.sqliteInstructions = sqliteInstructionsParsed;

  return newOptions;
});

const anyValueChanged = computed(() => {
  const form: Partial<BackendOptions> = {
    dataDirectory: get(userDataDirectory),
    logDirectory: get(userLogDirectory),
    logFromOtherModules: get(logFromOtherModules),
    loglevel: get(logLevel),
    maxLogfilesNum: parseValue(get(maxLogFiles)),
    maxSizeInMbAllLogs: parseValue(get(maxLogSize)),
    sqliteInstructions: parseValue(get(sqliteInstructions)),
  };

  return !isEqual(form, get(initialOptions));
});

const { openDirectory } = useInterop();

const nonNegativeNumberRules = {
  nonNegative: helpers.withMessage(t('backend_settings.errors.min', { min: 0 }), and(numeric, minValue(0))),
  required: helpers.withMessage(t('backend_settings.errors.non_empty'), required),
};

const rules = {
  maxLogFiles: nonNegativeNumberRules,
  maxLogSize: nonNegativeNumberRules,
  sqliteInstructions: nonNegativeNumberRules,
};

const v$ = useVuelidate(
  rules,
  {
    maxLogFiles,
    maxLogSize,
    sqliteInstructions,
  },
  { $autoDirty: true },
);

watch(v$, ({ $invalid }) => {
  set(valid, !$invalid);
});

async function reset() {
  set(confirmReset, false);
  dismiss();
  await resetOptions();
}

async function selectDataDirectory() {
  if (get(selecting))
    return;

  try {
    const title = t('backend_settings.data_directory.select');
    const directory = await openDirectory(title);
    if (directory)
      set(userDataDirectory, directory);
  }
  finally {
    set(selecting, false);
  }
}

async function save() {
  dismiss();
  const newUserOptionsVal = get(newUserOptions);
  const keys = Object.keys(newUserOptionsVal);

  // If only loglevel changed, update configuration without restarting the backend
  if (keys.length === 1 && keys[0] === 'loglevel') {
    await updateBackendConfiguration(newUserOptionsVal.loglevel!);
    await applyUserOptions({ loglevel: newUserOptionsVal.loglevel }, true);
    await loadConfiguration();
  }
  else {
    await saveOptions(newUserOptionsVal);
  }
}

async function selectLogsDirectory() {
  if (get(selecting))
    return;

  set(selecting, true);
  try {
    const directory = await openDirectory(t('backend_settings.log_directory.select'));
    if (directory)
      set(userLogDirectory, directory);
  }
  finally {
    set(selecting, false);
  }
}

function dismiss() {
  emit('dismiss');
}

watch(dataDirectory, (directory) => {
  set(userDataDirectory, get(options).dataDirectory ?? directory);
});

const { show } = useConfirmStore();

function showResetConfirmation() {
  show(
    {
      message: t('backend_settings.confirm.message'),
      title: t('backend_settings.confirm.title'),
    },
    reset,
  );
}

onBeforeMount(async () => {
  await loadConfiguration();
});
</script>

<template>
  <BigDialog
    display
    :title="t('frontend_settings.title')"
    @cancel="dismiss()"
  >
    <div class="mb-4">
      <LanguageSetting use-local-setting />
    </div>

    <div class="mb-4">
      <RuiCardHeader class="p-0">
        <template #header>
          {{ t('backend_settings.title') }}
        </template>
        <template #subheader>
          {{ t('backend_settings.subtitle') }}
        </template>
      </RuiCardHeader>
    </div>

    <div class="flex flex-col gap-4">
      <RuiTextField
        v-model="userDataDirectory"
        data-cy="user-data-directory-input"
        :loading="!userDataDirectory"
        class="pt-2"
        variant="outlined"
        color="primary"
        :disabled="!!fileConfig.dataDirectory || !userDataDirectory"
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
            :disabled="!userDataDirectory"
            @click="selectDataDirectory()"
          >
            <RuiIcon name="lu-folder" />
          </RuiButton>
        </template>
      </RuiTextField>
      <RuiTextField
        v-model="userLogDirectory"
        data-cy="user-log-directory-input"
        :disabled="!!fileConfig.logDirectory"
        :hint="!!fileConfig.logDirectory ? t('backend_settings.config_file_disabled') : undefined"
        variant="outlined"
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

    <RuiAccordions>
      <RuiAccordion
        data-cy="onboarding-setting__advance"
        header-class="py-4"
        eager
      >
        <template #header>
          {{ t('backend_settings.advanced') }}
        </template>
        <div class="py-2">
          <RuiTextField
            v-model="maxLogSize"
            data-cy="max-log-size-input"
            class="mb-4"
            variant="outlined"
            color="primary"
            :hint="
              !!fileConfig.maxSizeInMbAllLogs
                ? t('backend_settings.config_file_disabled')
                : t('backend_settings.max_log_size.hint')
            "
            :label="t('backend_settings.max_log_size.label')"
            :disabled="!!fileConfig.maxSizeInMbAllLogs"
            :loading="!configuration || !defaultBackendArguments"
            :error-messages="toMessages(v$.maxLogSize)"
            type="number"
          >
            <template #append>
              <SettingResetButton
                v-if="!isMaxSizeDefault"
                data-cy="reset-max-log-size"
                @click="resetDefaultArguments('size')"
              />
            </template>
          </RuiTextField>
          <RuiTextField
            v-model="maxLogFiles"
            data-cy="max-log-files-input"
            variant="outlined"
            color="primary"
            class="mb-4"
            :hint="t('backend_settings.max_log_files.hint')"
            :label="
              !!fileConfig.maxLogfilesNum
                ? t('backend_settings.config_file_disabled')
                : t('backend_settings.max_log_files.label')
            "
            :disabled="!!fileConfig.maxLogfilesNum"
            :loading="!configuration || !defaultBackendArguments"
            :error-messages="toMessages(v$.maxLogFiles)"
            type="number"
          >
            <template #append>
              <SettingResetButton
                v-if="!isMaxLogFilesDefault"
                data-cy="reset-max-log-files"
                @click="resetDefaultArguments('files')"
              />
            </template>
          </RuiTextField>

          <RuiTextField
            v-model="sqliteInstructions"
            data-cy="sqlite-instructions-input"
            variant="outlined"
            color="primary"
            class="mb-4"
            :hint="
              !!fileConfig.sqliteInstructions
                ? t('backend_settings.config_file_disabled')
                : t('backend_settings.sqlite_instructions.hint')
            "
            :label="t('backend_settings.sqlite_instructions.label')"
            :disabled="!!fileConfig.sqliteInstructions"
            :loading="!configuration || !defaultBackendArguments"
            :error-messages="toMessages(v$.sqliteInstructions)"
            type="number"
          >
            <template #append>
              <SettingResetButton
                v-if="!isSqliteInstructionsDefaults"
                data-cy="reset-sqlite-instructions"
                @click="resetDefaultArguments('instructions')"
              />
            </template>
          </RuiTextField>

          <RuiCheckbox
            v-model="logFromOtherModules"
            color="primary"
            data-cy="log-from-other-modules-checkbox"
            :label="t('backend_settings.log_from_other_modules.label')"
            :disabled="fileConfig.logFromOtherModules"
            :hint="
              fileConfig.logFromOtherModules
                ? t('backend_settings.config_file_disabled')
                : t('backend_settings.log_from_other_modules.hint')
            "
          >
            {{ t('backend_settings.log_from_other_modules.label') }}
          </RuiCheckbox>
        </div>
      </RuiAccordion>
    </RuiAccordions>

    <template #footer>
      <div class="flex justify-end w-full gap-2">
        <RuiButton
          variant="text"
          color="primary"
          @click="dismiss()"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          variant="outlined"
          color="primary"
          @click="showResetConfirmation()"
        >
          {{ t('backend_settings.actions.reset') }}
        </RuiButton>
        <RuiButton
          data-cy="onboarding-setting__submit-button"
          color="primary"
          :disabled="!anyValueChanged || !valid"
          type="submit"
          @click="save()"
        >
          {{ t('common.actions.save') }}
        </RuiButton>
      </div>
    </template>
  </BigDialog>
</template>
