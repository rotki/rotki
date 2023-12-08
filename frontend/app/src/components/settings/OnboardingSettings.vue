<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import {
  and,
  helpers,
  minValue,
  numeric,
  required
} from '@vuelidate/validators';
import { type Ref } from 'vue';
import { isEqual } from 'lodash-es';
import { type BackendOptions } from '@/electron-main/ipc';
import { type Writeable } from '@/types';
import { LogLevel } from '@/utils/log-level';
import { type BackendConfiguration } from '@/types/backend';
import { toMessages } from '@/utils/validation';

const emit = defineEmits<{
  (e: 'dismiss'): void;
}>();

const { t } = useI18n();

const { dataDirectory, defaultBackendArguments } = storeToRefs(useMainStore());

const userDataDirectory: Ref<string> = ref('');
const userLogDirectory: Ref<string> = ref('');
const logFromOtherModules: Ref<boolean> = ref(false);
const valid: Ref<boolean> = ref(false);

const maxLogSize: Ref<string> = ref('0');
const sqliteInstructions: Ref<string> = ref('0');
const maxLogFiles: Ref<string> = ref('0');

const { backendSettings } = useSettingsApi();

const selecting: Ref<boolean> = ref(false);
const confirmReset: Ref<boolean> = ref(false);
const configuration: Ref<BackendConfiguration> = asyncComputed(() =>
  backendSettings()
);

const initialOptions: ComputedRef<Partial<BackendOptions>> = computed(() => {
  const config = get(configuration);
  const opts = get(options);
  const defaults = get(defaultBackendArguments);
  return {
    loglevel: opts.loglevel ?? get(defaultLogLevel),
    dataDirectory: opts.dataDirectory ?? get(dataDirectory),
    logDirectory: opts.logDirectory ?? get(defaultLogDirectory),
    logFromOtherModules: opts.logFromOtherModules ?? false,
    maxLogfilesNum:
      opts.maxLogfilesNum ??
      config?.maxLogfilesNum?.value ??
      defaults.maxLogfilesNum,
    maxSizeInMbAllLogs:
      opts.maxSizeInMbAllLogs ??
      config?.maxSizeInMbAllLogs?.value ??
      defaults.maxSizeInMbAllLogs,
    sqliteInstructions:
      opts.sqliteInstructions ??
      config?.sqliteInstructions?.value ??
      defaults.sqliteInstructions
  };
});

const parseValue = (value?: string) => {
  if (!value) {
    return 0;
  }
  const parsedValue = Number.parseInt(value);
  return Number.isNaN(parsedValue) ? 0 : parsedValue;
};

const stringifyValue = (value?: number) => {
  if (!value) {
    return '0';
  }
  return value.toString();
};

const loaded = async () => {
  const initial = get(initialOptions);

  set(logLevel, initial.loglevel);
  set(userDataDirectory, initial.dataDirectory);
  set(userLogDirectory, initial.logDirectory);
  set(logFromOtherModules, initial.logFromOtherModules);
  set(maxLogFiles, stringifyValue(initial.maxLogfilesNum));
  set(maxLogSize, stringifyValue(initial.maxSizeInMbAllLogs));
  set(sqliteInstructions, stringifyValue(initial.sqliteInstructions));
};

const {
  resetOptions,
  saveOptions,
  fileConfig,
  logLevel,
  defaultLogLevel,
  defaultLogDirectory,
  options
} = useBackendManagement(loaded);

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

const resetDefaultArguments = (field: 'files' | 'size' | 'instructions') => {
  const defaults = get(defaultBackendArguments);
  if (field === 'files') {
    set(maxLogFiles, stringifyValue(defaults.maxLogfilesNum));
  } else if (field === 'size') {
    set(maxLogSize, stringifyValue(defaults.maxSizeInMbAllLogs));
  } else if (field === 'instructions') {
    set(sqliteInstructions, stringifyValue(defaults.sqliteInstructions));
  }
};

const newUserOptions = computed(() => {
  const initial = get(initialOptions);
  const newOptions: Writeable<Partial<BackendOptions>> = {};

  const level = get(logLevel);
  if (level !== initial.loglevel) {
    newOptions.loglevel = level;
  }

  const userData = get(userDataDirectory);
  if (userData !== initial.dataDirectory) {
    newOptions.dataDirectory = userData;
  }

  const userLog = get(userLogDirectory);
  if (userLog !== initial.logDirectory) {
    newOptions.logDirectory = userLog;
  }

  const logFromOther = get(logFromOtherModules);
  if (logFromOther !== initial.logFromOtherModules) {
    newOptions.logFromOtherModules = logFromOther;
  }
  if (!get(isMaxLogFilesDefault)) {
    newOptions.maxLogfilesNum = parseValue(get(maxLogFiles));
  }

  if (!get(isMaxSizeDefault)) {
    newOptions.maxSizeInMbAllLogs = parseValue(get(maxLogSize));
  }

  if (!get(isSqliteInstructionsDefaults)) {
    newOptions.sqliteInstructions = parseValue(get(sqliteInstructions));
  }

  return newOptions;
});

const anyValueChanged = computed(() => {
  const form: Partial<BackendOptions> = {
    loglevel: get(logLevel),
    dataDirectory: get(userDataDirectory),
    logDirectory: get(userLogDirectory),
    logFromOtherModules: get(logFromOtherModules),
    maxSizeInMbAllLogs: parseValue(get(maxLogSize)),
    sqliteInstructions: parseValue(get(sqliteInstructions)),
    maxLogfilesNum: parseValue(get(maxLogFiles))
  };

  return !isEqual(form, get(initialOptions));
});

const { openDirectory } = useInterop();

const nonNegativeNumberRules = {
  required: helpers.withMessage(
    t('backend_settings.errors.non_empty'),
    required
  ),
  nonNegative: helpers.withMessage(
    t('backend_settings.errors.min', { min: 0 }),
    and(numeric, minValue(0))
  )
};

const rules = {
  maxLogSize: nonNegativeNumberRules,
  maxLogFiles: nonNegativeNumberRules,
  sqliteInstructions: nonNegativeNumberRules
};

const v$ = useVuelidate(
  rules,
  {
    maxLogSize,
    maxLogFiles,
    sqliteInstructions
  },
  { $autoDirty: true }
);

watch(v$, ({ $invalid }) => {
  set(valid, !$invalid);
});

const icon = (level: LogLevel): string => {
  if (level === LogLevel.DEBUG) {
    return 'bug-line';
  } else if (level === LogLevel.INFO) {
    return 'information-line';
  } else if (level === LogLevel.WARNING) {
    return 'alert-line';
  } else if (level === LogLevel.ERROR) {
    return 'error-warning-line';
  } else if (level === LogLevel.CRITICAL) {
    return 'virus-line';
  } else if (level === LogLevel.TRACE) {
    return 'file-search-line';
  }
  throw new Error(`Invalid option: ${level}`);
};

const reset = async function () {
  set(confirmReset, false);
  dismiss();
  await resetOptions();
};

const selectDataDirectory = async function () {
  if (get(selecting)) {
    return;
  }

  try {
    const title = t('backend_settings.data_directory.select');
    const directory = await openDirectory(title);
    if (directory) {
      set(userDataDirectory, directory);
    }
  } finally {
    set(selecting, false);
  }
};

async function save() {
  dismiss();
  await saveOptions(get(newUserOptions));
}

async function selectLogsDirectory() {
  if (get(selecting)) {
    return;
  }
  set(selecting, true);
  try {
    const directory = await openDirectory(
      t('backend_settings.log_directory.select')
    );
    if (directory) {
      set(userLogDirectory, directory);
    }
  } finally {
    set(selecting, false);
  }
}

const dismiss = () => {
  emit('dismiss');
};

watch(dataDirectory, directory => {
  set(userDataDirectory, get(options).dataDirectory ?? directory);
});

const levels = Object.values(LogLevel);

const { show } = useConfirmStore();

const showResetConfirmation = () => {
  show(
    {
      title: t('backend_settings.confirm.title'),
      message: t('backend_settings.confirm.message')
    },
    reset
  );
};
</script>

<template>
  <Card contained class="pt-4">
    <div class="mb-4">
      <CardTitle class="font-medium">
        {{ t('frontend_settings.title') }}
      </CardTitle>
    </div>

    <div class="mb-8">
      <LanguageSetting use-local-setting class="mb-10" />
    </div>

    <div class="mb-4">
      <CardTitle class="font-medium">
        {{ t('backend_settings.title') }}
      </CardTitle>
      <VCardSubtitle class="pa-0">
        {{ t('backend_settings.subtitle') }}
      </VCardSubtitle>
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
            <RuiIcon name="folder-line" />
          </RuiButton>
        </template>
      </RuiTextField>
      <RuiTextField
        v-model="userLogDirectory"
        data-cy="user-log-directory-input"
        :disabled="!!fileConfig.logDirectory"
        :hint="
          !!fileConfig.logDirectory
            ? t('backend_settings.config_file_disabled')
            : undefined
        "
        variant="outlined"
        color="primary"
        :label="t('backend_settings.settings.log_directory.label')"
        readonly
        @click="selectLogsDirectory()"
      >
        <template #append>
          <RuiButton variant="text" icon @click="selectLogsDirectory()">
            <RuiIcon name="folder-line" />
          </RuiButton>
        </template>
      </RuiTextField>

      <VSelect
        v-model="logLevel"
        :items="levels"
        class="loglevel-input"
        :disabled="!!fileConfig.loglevel"
        :label="t('backend_settings.settings.log_level.label')"
        :persistent-hint="!!fileConfig.loglevel"
        :hint="
          !!fileConfig.loglevel
            ? t('backend_settings.config_file_disabled')
            : null
        "
        outlined
      >
        <template #item="{ item }">
          <div class="flex items-center gap-4">
            <RuiIcon class="text-rui-text-secondary" :name="icon(item)" />
            {{ item.toLocaleLowerCase() }}
          </div>
        </template>
        <template #selection="{ item }">
          <div class="flex items-center gap-4">
            <RuiIcon class="text-rui-text-secondary" :name="icon(item)" />
            {{ item.toLocaleLowerCase() }}
          </div>
        </template>
      </VSelect>

      <VExpansionPanels flat>
        <VExpansionPanel>
          <VExpansionPanelHeader data-cy="onboarding-setting__advance-toggle">
            {{ t('backend_settings.advanced') }}
          </VExpansionPanelHeader>
          <VExpansionPanelContent>
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
          </VExpansionPanelContent>
        </VExpansionPanel>
      </VExpansionPanels>
    </div>

    <template #buttons>
      <div class="flex justify-end w-full gap-2">
        <RuiButton variant="text" color="primary" @click="dismiss()">
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
          @click="save()"
        >
          {{ t('common.actions.save') }}
        </RuiButton>
      </div>
    </template>
  </Card>
</template>

<style scoped lang="scss">
:deep(.v-expansion-panel) {
  .v-expansion-panel {
    &-content {
      &__wrap {
        padding: 0 0 16px;
      }
    }

    &-header {
      padding: 16px 0;
    }
  }
}
</style>
