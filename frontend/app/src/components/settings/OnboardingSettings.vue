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
import { type BackendOptions } from '@/electron-main/ipc';
import { type Writeable } from '@/types';
import { LogLevel } from '@/utils/log-level';
import {
  type BackendConfiguration,
  type DefaultBackendArguments
} from '@/types/backend';

const emit = defineEmits<{
  (e: 'dismiss'): void;
}>();

const { dataDirectory } = storeToRefs(useMainStore());

const userDataDirectory: Ref<string> = ref('');
const userLogDirectory: Ref<string> = ref('');
const logFromOtherModules: Ref<boolean> = ref(false);
const maxLogSize: Ref<number> = ref(0);
const sqliteInstructions: Ref<number> = ref(0);
const maxLogFiles: Ref<number> = ref(0);
const formValid: Ref<boolean> = ref(false);

const { backendSettings } = useSettingsApi();

const selecting: Ref<boolean> = ref(false);
const confirmReset: Ref<boolean> = ref(false);
const configuration: Ref<BackendConfiguration> = asyncComputed(() =>
  backendSettings()
);

const { info } = useInfoApi();
const defaultArguments: Ref<DefaultBackendArguments> = asyncComputed(
  () => info().then(info => info.backendDefaultArguments),
  {
    maxLogfilesNum: 0,
    maxSizeInMbAllLogs: 0,
    sqliteInstructions: 0
  }
);

const { t } = useI18n();

const loaded = async () => {
  const config = get(configuration);
  const opts = get(options);
  const defaults = get(defaultArguments);

  set(userDataDirectory, opts.dataDirectory ?? get(dataDirectory));
  set(userLogDirectory, opts.logDirectory ?? get(defaultLogDirectory));
  set(logLevel, opts.loglevel ?? get(defaultLogLevel));
  set(logFromOtherModules, opts.logFromOtherModules ?? false);
  set(
    maxLogFiles,
    opts.maxLogfilesNum ??
      config.maxLogfilesNum.value ??
      defaults.maxLogfilesNum
  );
  set(
    maxLogSize,
    opts.maxSizeInMbAllLogs ??
      config.maxSizeInMbAllLogs.value ??
      defaults.maxSizeInMbAllLogs
  );
  set(
    sqliteInstructions,
    opts.sqliteInstructions ??
      config.sqliteInstructions.value ??
      defaults.sqliteInstructions
  );
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
  const defaults = get(defaultArguments);
  return defaults.maxLogfilesNum === get(maxLogFiles);
});

const isMaxSizeDefault = computed(() => {
  const defaults = get(defaultArguments);
  return defaults.maxSizeInMbAllLogs === get(maxLogSize);
});

const isSqliteInstructionsDefaults = computed(() => {
  const defaults = get(defaultArguments);
  return defaults.sqliteInstructions === get(sqliteInstructions);
});

const resetDefaultArguments = (field: 'files' | 'size' | 'instructions') => {
  const defaults = get(defaultArguments);
  if (field === 'files') {
    set(maxLogFiles, defaults.maxLogfilesNum);
  } else if (field === 'size') {
    set(maxLogSize, defaults.maxSizeInMbAllLogs);
  } else if (field === 'instructions') {
    set(sqliteInstructions, defaults.sqliteInstructions);
  }
};

const newUserOptions = computed(() => {
  const options: Writeable<Partial<BackendOptions>> = {};
  const level = get(logLevel);
  const defaultLevel = get(defaultLogLevel);
  if (level !== defaultLevel) {
    options.loglevel = level;
  }

  const userLog = get(userLogDirectory);
  if (userLog !== get(defaultLogDirectory)) {
    options.logDirectory = userLog;
  }

  const logFromOther = get(logFromOtherModules);
  if (logFromOther) {
    options.logFromOtherModules = true;
  }

  const userData = get(userDataDirectory);
  if (userData !== get(dataDirectory)) {
    options.dataDirectory = userData;
  }

  if (isDefined(defaultArguments)) {
    const defaults = get(defaultArguments);
    if (defaults.maxLogfilesNum !== get(maxLogFiles)) {
      options.maxLogfilesNum = get(maxLogFiles);
    } else {
      delete options.maxLogfilesNum;
    }

    if (defaults.maxSizeInMbAllLogs !== get(maxLogSize)) {
      options.maxSizeInMbAllLogs = get(maxLogSize);
    } else {
      delete options.maxSizeInMbAllLogs;
    }

    if (defaults.sqliteInstructions !== get(sqliteInstructions)) {
      options.sqliteInstructions = get(sqliteInstructions);
    } else {
      delete options.sqliteInstructions;
    }
  }

  return options;
});

const valid = computed(() => {
  const newOptions = get(newUserOptions);
  const oldOptions = get(options);
  const defaultLevel = get(defaultLogLevel);
  const newLogLevel = newOptions.loglevel ?? defaultLevel;
  const oldLogLevel = oldOptions.loglevel ?? defaultLevel;
  const updatedKeys = Object.keys(newOptions).filter(s => s !== 'loglevel');
  return updatedKeys.length > 0 || newLogLevel !== oldLogLevel;
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
  set(formValid, !$invalid);
});

const icon = (level: LogLevel): string => {
  if (level === LogLevel.DEBUG) {
    return 'mdi-bug';
  } else if (level === LogLevel.INFO) {
    return 'mdi-information';
  } else if (level === LogLevel.WARNING) {
    return 'mdi-alert';
  } else if (level === LogLevel.ERROR) {
    return 'mdi-alert-circle';
  } else if (level === LogLevel.CRITICAL) {
    return 'mdi-alert-decagram';
  } else if (level === LogLevel.TRACE) {
    return 'mdi-magnify-scan';
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

watch(defaultArguments, args => {
  if (!get(maxLogSize) && args.maxSizeInMbAllLogs) {
    set(maxLogSize, args.maxSizeInMbAllLogs);
  }

  if (!get(maxLogFiles) && args.maxLogfilesNum) {
    set(maxLogFiles, args.maxLogfilesNum);
  }

  if (!get(sqliteInstructions) && args.sqliteInstructions) {
    set(sqliteInstructions, args.sqliteInstructions);
  }
});
</script>

<template>
  <card contained class="pt-4">
    <div class="mb-4">
      <card-title class="font-weight-medium">
        {{ t('frontend_settings.title') }}
      </card-title>
    </div>

    <div class="mb-8">
      <language-setting use-local-setting class="mb-10" />
    </div>

    <div class="mb-4">
      <card-title class="font-weight-medium">
        {{ t('backend_settings.title') }}
      </card-title>
      <v-card-subtitle class="pa-0">
        {{ t('backend_settings.subtitle') }}
      </v-card-subtitle>
    </div>

    <v-text-field
      v-model="userDataDirectory"
      :loading="!userDataDirectory"
      class="pt-2"
      outlined
      :disabled="!!fileConfig.dataDirectory || !userDataDirectory"
      persistent-hint
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
        <v-btn
          icon
          :disabled="!userDataDirectory"
          @click="selectDataDirectory()"
        >
          <v-icon>mdi-folder</v-icon>
        </v-btn>
      </template>
    </v-text-field>

    <v-form :value="formValid">
      <v-text-field
        v-model="userLogDirectory"
        :disabled="!!fileConfig.logDirectory"
        :persistent-hint="!!fileConfig.logDirectory"
        :hint="
          !!fileConfig.logDirectory
            ? t('backend_settings.config_file_disabled')
            : null
        "
        outlined
        :label="t('backend_settings.settings.log_directory.label')"
        readonly
        @click="selectLogsDirectory()"
      >
        <template #append>
          <v-btn icon @click="selectLogsDirectory()">
            <v-icon>mdi-folder</v-icon>
          </v-btn>
        </template>
      </v-text-field>

      <v-select
        v-model="logLevel"
        :items="levels"
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
          <v-row align="center">
            <v-col cols="auto">
              <v-icon>{{ icon(item) }}</v-icon>
            </v-col>
            <v-col>{{ item.toLocaleLowerCase() }}</v-col>
          </v-row>
        </template>
        <template #selection="{ item }">
          <v-row align="center">
            <v-col cols="auto">
              <v-icon>{{ icon(item) }}</v-icon>
            </v-col>
            <v-col>{{ item.toLocaleLowerCase() }}</v-col>
          </v-row>
        </template>
      </v-select>

      <v-expansion-panels flat>
        <v-expansion-panel>
          <v-expansion-panel-header>
            {{ t('backend_settings.advanced') }}
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <v-text-field
              v-model.number="maxLogSize"
              outlined
              :hint="
                !!fileConfig.maxSizeInMbAllLogs
                  ? t('backend_settings.config_file_disabled')
                  : t('backend_settings.max_log_size.hint')
              "
              :label="t('backend_settings.max_log_size.label')"
              :disabled="fileConfig.maxSizeInMbAllLogs"
              :persistent-hint="!!fileConfig.maxSizeInMbAllLogs"
              :loading="!configuration || !defaultArguments"
              :error-messages="v$.maxLogSize.$errors.map(e => e.$message)"
              type="number"
            >
              <template #append>
                <setting-reset-button
                  v-if="!isMaxSizeDefault"
                  @click="resetDefaultArguments('size')"
                />
              </template>
            </v-text-field>
            <v-text-field
              v-model.number="maxLogFiles"
              outlined
              :hint="t('backend_settings.max_log_files.hint')"
              :label="
                !!fileConfig.maxLogfilesNum
                  ? t('backend_settings.config_file_disabled')
                  : t('backend_settings.max_log_files.label')
              "
              :disabled="fileConfig.maxLogfilesNum"
              :persistent-hint="!!fileConfig.maxLogfilesNum"
              :loading="!configuration || !defaultArguments"
              :error-messages="v$.maxLogFiles.$errors.map(e => e.$message)"
              type="number"
            >
              <template #append>
                <setting-reset-button
                  v-if="!isMaxLogFilesDefault"
                  @click="resetDefaultArguments('files')"
                />
              </template>
            </v-text-field>

            <v-text-field
              v-model.number="sqliteInstructions"
              outlined
              :hint="
                !!fileConfig.sqliteInstructions
                  ? t('backend_settings.config_file_disabled')
                  : t('backend_settings.sqlite_instructions.hint')
              "
              :label="t('backend_settings.sqlite_instructions.label')"
              :disabled="fileConfig.sqliteInstructions"
              :persistent-hint="!!fileConfig.sqliteInstructions"
              :loading="!configuration || !defaultArguments"
              :error-messages="
                v$.sqliteInstructions.$errors.map(e => e.$message)
              "
              type="number"
            >
              <template #append>
                <setting-reset-button
                  v-if="!isSqliteInstructionsDefaults"
                  @click="resetDefaultArguments('instructions')"
                />
              </template>
            </v-text-field>

            <v-checkbox
              v-model="logFromOtherModules"
              :label="t('backend_settings.log_from_other_modules.label')"
              :disabled="fileConfig.logFromOtherModules"
              persistent-hint
              :hint="
                fileConfig.logFromOtherModules
                  ? t('backend_settings.config_file_disabled')
                  : t('backend_settings.log_from_other_modules.hint')
              "
            />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-form>

    <template #buttons>
      <v-spacer />
      <v-btn depressed @click="dismiss()">
        {{ t('common.actions.cancel') }}
      </v-btn>
      <v-btn depressed @click="showResetConfirmation()">
        {{ t('backend_settings.actions.reset') }}
      </v-btn>
      <v-btn
        depressed
        color="primary"
        :disabled="!valid || !formValid"
        @click="save()"
      >
        {{ t('common.actions.save') }}
      </v-btn>
    </template>
  </card>
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
