<template>
  <card contained class="pt-4">
    <div class="mb-4">
      <card-title class="font-weight-medium">
        {{ tc('frontend_settings.title') }}
      </card-title>
    </div>

    <div class="mb-8">
      <language-setting use-local-setting class="mb-10" />
    </div>

    <div class="mb-4">
      <card-title class="font-weight-medium">
        {{ tc('backend_settings.title') }}
      </card-title>
      <v-card-subtitle class="pa-0">
        {{ tc('backend_settings.subtitle') }}
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
          ? tc('backend_settings.config_file_disabled')
          : tc('backend_settings.settings.data_directory.hint')
      "
      :label="tc('backend_settings.settings.data_directory.label')"
      readonly
      @click="selectDataDirectory"
    >
      <template #append>
        <v-btn icon :disabled="!userDataDirectory" @click="selectDataDirectory">
          <v-icon>mdi-folder</v-icon>
        </v-btn>
      </template>
    </v-text-field>

    <v-form v-model="formValid">
      <v-text-field
        v-model="userLogDirectory"
        :disabled="!!fileConfig.logDirectory"
        :persistent-hint="!!fileConfig.logDirectory"
        :hint="
          !!fileConfig.logDirectory
            ? tc('backend_settings.config_file_disabled')
            : null
        "
        outlined
        :label="tc('backend_settings.settings.log_directory.label')"
        readonly
        @click="selectLogsDirectory"
      >
        <template #append>
          <v-btn icon @click="selectLogsDirectory">
            <v-icon>mdi-folder</v-icon>
          </v-btn>
        </template>
      </v-text-field>

      <v-select
        v-model="logLevel"
        :items="levels"
        :disabled="!!fileConfig.loglevel"
        :label="tc('backend_settings.settings.log_level.label')"
        :persistent-hint="!!fileConfig.loglevel"
        :hint="
          !!fileConfig.loglevel
            ? tc('backend_settings.config_file_disabled')
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
            {{ tc('backend_settings.advanced') }}
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <v-text-field
              v-model="maxLogSize"
              outlined
              :hint="
                !!fileConfig.maxSizeInMbAllLogs
                  ? tc('backend_settings.config_file_disabled')
                  : tc('backend_settings.max_log_size.hint')
              "
              :label="tc('backend_settings.max_log_size.label')"
              :disabled="fileConfig.maxSizeInMbAllLogs"
              :persistent-hint="!!fileConfig.maxSizeInMbAllLogs"
              :clearable="!isDefault(configuration?.maxSizeInMbAllLogs)"
              :loading="!configuration"
              :rules="nonNegativeNumberRules"
              type="number"
            />
            <v-text-field
              v-model="maxLogFiles"
              outlined
              :hint="tc('backend_settings.max_log_files.hint')"
              :label="
                !!fileConfig.maxLogfilesNum
                  ? tc('backend_settings.config_file_disabled')
                  : tc('backend_settings.max_log_files.label')
              "
              :disabled="fileConfig.maxLogfilesNum"
              :persistent-hint="!!fileConfig.maxLogfilesNum"
              :clearable="!isDefault(configuration?.maxLogfilesNum)"
              :loading="!configuration"
              :rules="nonNegativeNumberRules"
              type="number"
            />

            <v-text-field
              v-model="sqliteInstructions"
              outlined
              :hint="
                !!fileConfig.sqliteInstructions
                  ? tc('backend_settings.config_file_disabled')
                  : tc('backend_settings.sqlite_instructions.hint')
              "
              :label="tc('backend_settings.sqlite_instructions.label')"
              :disabled="fileConfig.sqliteInstructions"
              :persistent-hint="!!fileConfig.sqliteInstructions"
              :clearable="!isDefault(configuration?.sqliteInstructions)"
              :loading="!configuration"
              :rules="nonNegativeNumberRules"
              type="number"
            />

            <v-checkbox
              v-model="logFromOtherModules"
              :label="tc('backend_settings.log_from_other_modules.label')"
              :disabled="!!fileConfig.logFromOtherModules"
              persistent-hint
              :hint="
                !!fileConfig.logFromOtherModules
                  ? tc('backend_settings.config_file_disabled')
                  : tc('backend_settings.log_from_other_modules.hint')
              "
            />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-form>

    <template #buttons>
      <v-spacer />
      <v-btn depressed @click="dismiss()">
        {{ tc('common.actions.cancel') }}
      </v-btn>
      <v-btn depressed @click="confirmReset = true">
        {{ tc('backend_settings.actions.reset') }}
      </v-btn>
      <v-btn
        depressed
        color="primary"
        :disabled="!valid || !formValid"
        @click="save()"
      >
        {{ tc('common.actions.save') }}
      </v-btn>
    </template>

    <confirm-dialog
      v-if="confirmReset"
      :message="tc('backend_settings.confirm.message')"
      :display="confirmReset"
      :title="tc('backend_settings.confirm.title')"
      @confirm="reset"
      @cancel="confirmReset = false"
    />
  </card>
</template>

<script setup lang="ts">
import { Ref } from 'vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import LanguageSetting from '@/components/settings/general/language/LanguageSetting.vue';
import { useBackendManagement } from '@/composables/backend';
import { useInterop } from '@/electron-interop';
import { BackendOptions } from '@/electron-main/ipc';
import { useSettingsApi } from '@/services/settings/settings-api';
import {
  BackendConfiguration,
  NumericBackendArgument
} from '@/services/types-api';
import { useMainStore } from '@/store/main';
import { Properties, Writeable } from '@/types';
import { LogLevel } from '@/utils/log-level';

type Args = {
  value: string;
  arg: NumericBackendArgument;
  options: Writeable<Partial<BackendOptions>>;
  key: Properties<BackendOptions, number>;
};

const updateArgument = (args: Args) => {
  if (args.value !== args.arg.value.toString()) {
    const numeric = parseInt(args.value);
    if (isFinite(numeric) && !isNaN(numeric)) {
      args.options[args.key] = numeric;
    } else {
      delete args.options[args.key];
    }
  }
};

const emit = defineEmits<{
  (e: 'dismiss'): void;
}>();

const { dataDirectory } = storeToRefs(useMainStore());

const userDataDirectory: Ref<string> = ref('');
const userLogDirectory: Ref<string> = ref('');
const logFromOtherModules: Ref<boolean> = ref(false);
const maxLogSize: Ref<string> = ref('');
const sqliteInstructions: Ref<string> = ref('');
const maxLogFiles: Ref<string> = ref('');
const formValid: Ref<boolean> = ref(false);

const api = useSettingsApi();

const selecting: Ref<boolean> = ref(false);
const confirmReset: Ref<boolean> = ref(false);
const configuration = asyncComputed<BackendConfiguration>(() =>
  api.backendSettings()
);

const { tc } = useI18n();

const loaded = async () => {
  const config = get(configuration);
  const opts = get(options);
  set(userDataDirectory, opts.dataDirectory ?? get(dataDirectory));
  set(userLogDirectory, opts.logDirectory ?? get(defaultLogDirectory));
  set(logLevel, opts.loglevel ?? get(defaultLogLevel));
  set(logFromOtherModules, opts.logFromOtherModules ?? false);
  set(
    maxLogFiles,
    (opts.maxLogfilesNum ?? config.maxLogfilesNum.value).toString()
  );
  set(
    maxLogSize,
    (opts.maxSizeInMbAllLogs ?? config.maxSizeInMbAllLogs.value).toString()
  );
  set(
    sqliteInstructions,
    (opts.sqliteInstructions ?? config.sqliteInstructions.value).toString()
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

  const config = get(configuration);
  if (config) {
    updateArgument({
      value: get(maxLogFiles),
      arg: config.maxLogfilesNum,
      options,
      key: 'maxLogfilesNum'
    });
    updateArgument({
      value: get(maxLogSize),
      arg: config.maxSizeInMbAllLogs,
      options,
      key: 'maxSizeInMbAllLogs'
    });
    updateArgument({
      value: get(sqliteInstructions),
      arg: config.sqliteInstructions,
      options,
      key: 'sqliteInstructions'
    });
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

const nonNegativeNumberRules = computed(() => {
  return [
    (v: string) => !!v || tc('backend_settings.errors.non_empty'),
    (v: string) =>
      parseInt(v) >= 0 || tc('backend_settings.errors.min', 0, { min: 0 })
  ];
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

const isDefault = (prop?: NumericBackendArgument) => prop?.isDefault;

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
    let title = tc('backend_settings.data_directory.select');
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
      tc('backend_settings.log_directory.select')
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
</script>

<style scoped lang="scss">
:deep() {
  .v-expansion-panel-content {
    &__wrap {
      padding: 0 0 16px;
    }
  }

  .v-expansion-panel-header {
    padding: 16px 0;
  }
}
</style>
