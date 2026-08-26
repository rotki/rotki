<script setup lang="ts">
import type { BackendOptions } from '@shared/ipc';
import type { BackendConfiguration } from '@/modules/shell/app/backend';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useForm } from '@/modules/core/form/use-form';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import AdvancedBackendSettings from '@/modules/settings/backend/AdvancedBackendSettings.vue';
import { resolveInitialBackendOptions } from '@/modules/settings/backend/backend-initial-options';
import {
  type AdvancedBackendField,
  backendDefaultsState,
  type BackendNumericField,
  type BackendNumericFields,
  backendNumericSchema,
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

const { backendSettings } = useSettingsApi();
const { applyLogLevelChange } = useLogLevelUpdate();

const selecting = ref<boolean>(false);
const confirmReset = ref<boolean>(false);
const configuration = ref<BackendConfiguration>();

async function loadConfiguration(): Promise<void> {
  set(configuration, await backendSettings());
}

/**
 * Only the three numeric fields are validated, so the form owns just those.
 * Everything else stays on plain refs, and whether anything changed is still a
 * comparison against the initial options rather than the form's own baseline.
 * `submit` is a no-op: `save()` decides between a full save and a log-level
 * only update, and referencing it from here would be a cycle.
 */
const form = useForm<BackendNumericFields, BackendNumericFields>({
  initial: (): BackendNumericFields => ({ maxLogFiles: '0', maxLogSize: '0', sqliteInstructions: '0' }),
  schema: backendNumericSchema({
    min: t('backend_settings.errors.min', { min: 0 }),
    nonEmpty: t('backend_settings.errors.non_empty'),
  }),
  submit: async (): Promise<{ success: boolean }> => ({ success: true }),
  transform: (state): BackendNumericFields => ({ ...state }),
});

/** `form.valid` is a `ComputedRef` on a plain object, so a template binding would never unwrap it. */
const invalid = computed<boolean>(() => !get(form.valid));

/** Vuelidate ran with `$autoDirty`, so an edited field showed its error straight away. */
function updateField(field: BackendNumericField, value: string): void {
  form.state[field] = value;
  form.touch(field);
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
  if (!get(configuration)) {
    await loadConfiguration();
  }
  const initial = get(initialOptions);

  set(modelLogLevel, initial.loglevel);
  set(userDataDirectory, initial.dataDirectory);
  set(userLogDirectory, initial.logDirectory);
  set(logFromOtherModules, initial.logFromOtherModules);
  form.reset({
    maxLogFiles: stringifyValue(initial.maxLogfilesNum),
    maxLogSize: stringifyValue(initial.maxSizeInMbAllLogs),
    sqliteInstructions: stringifyValue(initial.sqliteInstructions),
  });
}

const formFields = computed<BackendOptionsFormFields>(() => ({
  dataDirectory: get(userDataDirectory),
  logDirectory: get(userLogDirectory),
  logFromOtherModules: get(logFromOtherModules),
  loglevel: get(modelLogLevel),
  maxLogFiles: form.state.maxLogFiles,
  maxLogSize: form.state.maxLogSize,
  sqliteInstructions: form.state.sqliteInstructions,
}));

const atDefaults = computed(() => backendDefaultsState(get(formFields), get(defaultBackendArguments)));

function resetDefaultArguments(field: AdvancedBackendField): void {
  const defaults = get(defaultBackendArguments);
  if (field === 'files')
    updateField('maxLogFiles', stringifyValue(defaults.maxLogfilesNum));
  else if (field === 'size')
    updateField('maxLogSize', stringifyValue(defaults.maxSizeInMbAllLogs));
  else if (field === 'instructions')
    updateField('sqliteInstructions', stringifyValue(defaults.sqliteInstructions));
}

const newUserOptions = computed<Partial<BackendOptions>>(() => diffBackendOptions(get(formFields), get(initialOptions)));

const anyValueChanged = computed<boolean>(() => hasBackendOptionChanges(get(formFields), get(initialOptions)));

const { openDirectory } = useInterop();

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
        data-testid="onboarding-setting-advance"
        header-class="py-4"
        eager
      >
        <template #header>
          {{ t('backend_settings.advanced') }}
        </template>
        <AdvancedBackendSettings
          v-model:log-from-other-modules="logFromOtherModules"
          :at-defaults="atDefaults"
          :file-config="fileConfig"
          :loading="!configuration || !defaultBackendArguments"
          :max-log-files="form.state.maxLogFiles"
          :max-log-files-errors="form.errors('maxLogFiles')"
          :max-log-size="form.state.maxLogSize"
          :max-log-size-errors="form.errors('maxLogSize')"
          :sqlite-instructions="form.state.sqliteInstructions"
          :sqlite-instructions-errors="form.errors('sqliteInstructions')"
          @reset="resetDefaultArguments($event)"
          @update:max-log-files="updateField('maxLogFiles', $event)"
          @update:max-log-size="updateField('maxLogSize', $event)"
          @update:sqlite-instructions="updateField('sqliteInstructions', $event)"
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
          data-testid="onboarding-setting-reset"
          variant="outlined"
          color="primary"
          @click="showResetConfirmation()"
        >
          {{ t('backend_settings.actions.reset') }}
        </RuiButton>
        <RuiButton
          data-testid="onboarding-setting-submit"
          color="primary"
          :disabled="!anyValueChanged || invalid"
          type="submit"
          @click="save()"
        >
          {{ t('common.actions.save') }}
        </RuiButton>
      </div>
    </template>
  </BigDialog>
</template>
