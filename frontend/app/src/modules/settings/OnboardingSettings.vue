<script setup lang="ts">
import type { BackendOptions } from '@shared/ipc';
import type { BackendConfiguration } from '@/modules/shell/app/backend';
import useVuelidate from '@vuelidate/core';
import { and, helpers, minValue, numeric, required } from '@vuelidate/validators';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { toMessages } from '@/modules/core/common/validation/validation';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import AdvancedBackendSettings from '@/modules/settings/backend/AdvancedBackendSettings.vue';
import { resolveInitialBackendOptions } from '@/modules/settings/backend/backend-initial-options';
import {
  type AdvancedBackendField,
  backendDefaultsState,
  type BackendOptionsFormFields,
  diffBackendOptions,
  hasBackendOptionChanges,
  stringifyValue,
} from '@/modules/settings/backend/backend-options-form';
import LogLevelInput from '@/modules/settings/backend/LogLevelInput.vue';
import { useLogLevelUpdate } from '@/modules/settings/backend/use-log-level-update';
import LanguageSetting from '@/modules/settings/general/language/LanguageSetting.vue';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

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

const { backendSettings } = useSettingsApi();
const { applyLogLevelChange } = useLogLevelUpdate();

const selecting = ref<boolean>(false);
const confirmReset = ref<boolean>(false);
const configuration = ref<BackendConfiguration>();

async function loadConfiguration(): Promise<void> {
  set(configuration, await backendSettings());
}

const {
  applyUserOptions,
  defaultLogDirectory,
  defaultLogLevel,
  fileConfig,
  modelLogLevel,
  options,
  resetOptions,
  saveOptions,
} = useBackendManagement(loaded);

const initialOptions = computed<Partial<BackendOptions>>(() => resolveInitialBackendOptions(
  get(options),
  get(configuration),
  {
    dataDirectory: get(dataDirectory),
    logDirectory: get(defaultLogDirectory),
    defaultLogLevel: get(defaultLogLevel),
    defaults: get(defaultBackendArguments),
  },
));

async function loaded() {
  // Wait for the backend configuration before snapshotting initial values,
  // otherwise the loglevel fallback chain resolves to defaultLogLevel
  // (CRITICAL in prod) and the dropdown displays that stale value even
  // after the real backend level arrives. See regression #12079.
  if (!get(configuration)) {
    await loadConfiguration();
  }
  const initial = get(initialOptions);

  set(modelLogLevel, initial.loglevel);
  set(userDataDirectory, initial.dataDirectory);
  set(userLogDirectory, initial.logDirectory);
  set(logFromOtherModules, initial.logFromOtherModules);
  set(maxLogFiles, stringifyValue(initial.maxLogfilesNum));
  set(maxLogSize, stringifyValue(initial.maxSizeInMbAllLogs));
  set(sqliteInstructions, stringifyValue(initial.sqliteInstructions));
}

const formFields = computed<BackendOptionsFormFields>(() => ({
  dataDirectory: get(userDataDirectory),
  logDirectory: get(userLogDirectory),
  logFromOtherModules: get(logFromOtherModules),
  loglevel: get(modelLogLevel),
  maxLogFiles: get(maxLogFiles),
  maxLogSize: get(maxLogSize),
  sqliteInstructions: get(sqliteInstructions),
}));

const atDefaults = computed(() => backendDefaultsState(get(formFields), get(defaultBackendArguments)));

function resetDefaultArguments(field: AdvancedBackendField): void {
  const defaults = get(defaultBackendArguments);
  if (field === 'files')
    set(maxLogFiles, stringifyValue(defaults.maxLogfilesNum));
  else if (field === 'size')
    set(maxLogSize, stringifyValue(defaults.maxSizeInMbAllLogs));
  else if (field === 'instructions')
    set(sqliteInstructions, stringifyValue(defaults.sqliteInstructions));
}

const newUserOptions = computed<Partial<BackendOptions>>(() => diffBackendOptions(get(formFields), get(initialOptions)));

const anyValueChanged = computed<boolean>(() => hasBackendOptionChanges(get(formFields), get(initialOptions)));

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

  set(selecting, true);
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
    await applyLogLevelChange(newUserOptionsVal.loglevel!);
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
        data-testid="user-data-directory-input"
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
        data-testid="user-log-directory-input"
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
        v-model="modelLogLevel"
        :disabled="!!fileConfig.loglevel"
        :error-messages="!!fileConfig.loglevel ? t('backend_settings.config_file_disabled') : undefined"
      />
    </div>

    <RuiAccordions>
      <RuiAccordion
        data-testid="onboarding-setting__advance"
        header-class="py-4"
        eager
      >
        <template #header>
          {{ t('backend_settings.advanced') }}
        </template>
        <AdvancedBackendSettings
          v-model:log-from-other-modules="logFromOtherModules"
          v-model:max-log-files="maxLogFiles"
          v-model:max-log-size="maxLogSize"
          v-model:sqlite-instructions="sqliteInstructions"
          :at-defaults="atDefaults"
          :file-config="fileConfig"
          :loading="!configuration || !defaultBackendArguments"
          :max-log-files-errors="toMessages(v$.maxLogFiles)"
          :max-log-size-errors="toMessages(v$.maxLogSize)"
          :sqlite-instructions-errors="toMessages(v$.sqliteInstructions)"
          @reset="resetDefaultArguments($event)"
        />
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
          data-testid="onboarding-setting__reset-button"
          variant="outlined"
          color="primary"
          @click="showResetConfirmation()"
        >
          {{ t('backend_settings.actions.reset') }}
        </RuiButton>
        <RuiButton
          data-testid="onboarding-setting__submit-button"
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
