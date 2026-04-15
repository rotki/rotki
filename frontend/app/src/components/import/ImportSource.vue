<script setup lang="ts">
import type { ImportSourceType } from '@/modules/common/upload-types';
import type { TaskMeta } from '@/modules/tasks/types';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import FileUpload from '@/components/import/FileUpload.vue';
import DateFormatHelp from '@/components/settings/controls/DateFormatHelp.vue';
import { useImportDataApi } from '@/composables/api/import';
import { useInterop } from '@/composables/electron-interop';
import { refIsTruthy } from '@/composables/ref';
import { displayDateFormatter } from '@/data/date-formatter';
import { DateFormat } from '@/modules/common/date-format';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { toMessages } from '@/utils/validation';

interface ImportTaskMeta extends TaskMeta {
  readonly source: ImportSourceType;
}

const { source } = defineProps<{ source: ImportSourceType }>();

defineSlots<{
  'default': () => any;
  'hint': () => any;
  'upload-title': () => any;
}>();

const dateInputFormat = ref<string>();
const uploaded = ref(false);
const errorMessage = ref('');
const formatHelp = ref<boolean>(false);
const file = ref<File>();

const { t } = useI18n({ useScope: 'global' });
const { getPath } = useInterop();

const rules = {
  dateInputFormat: {
    required: helpers.withMessage(
      t('general_settings.date_display.validation.empty'),
      requiredIf(refIsTruthy(dateInputFormat)),
    ),
    validDate: helpers.withMessage(
      t('general_settings.date_display.validation.invalid'),
      (v: string | undefined): boolean => v === undefined || displayDateFormatter.containsValidDirectives(v),
    ),
  },
};

const v$ = useVuelidate(
  rules,
  {
    dateInputFormat,
  },
  { $autoDirty: true },
);

const dateInputFormatExample = computed(() => {
  const now = new Date();
  if (!get(dateInputFormat))
    return '';

  return displayDateFormatter.format(now, get(dateInputFormat)!);
});

const taskType = TaskType.IMPORT_CSV;
const { runTask } = useTaskHandler();
const { useIsTaskRunning } = useTaskStore();

const loading = useIsTaskRunning(taskType, { source });
const { importDataFrom, importFile } = useImportDataApi();

async function uploadPackaged(file: string): Promise<void> {
  const outcome = await runTask<boolean, ImportTaskMeta>(
    () => importDataFrom(source, file, get(dateInputFormat) || null),
    {
      type: taskType,
      meta: { source, title: t('file_upload.task.title', { source }) },
      unique: false,
    },
  );

  if (outcome.success) {
    if (outcome.result)
      set(uploaded, true);
  }
  else if (isActionableFailure(outcome)) {
    set(errorMessage, outcome.message);
  }
}

async function uploadFile(): Promise<void> {
  const fileVal = get(file);
  if (fileVal) {
    const path = getPath(fileVal);
    if (path) {
      await uploadPackaged(path);
    }
    else {
      const formData = new FormData();
      formData.append('source', source);
      formData.append('file', fileVal);
      formData.append('async_query', 'true');
      const dateInputFormatVal = get(dateInputFormat);
      if (dateInputFormatVal)
        formData.append('timestamp_format', dateInputFormatVal);

      const outcome = await runTask<boolean, ImportTaskMeta>(
        () => importFile(formData),
        {
          type: taskType,
          meta: { source, title: t('file_upload.task.title', { source }) },
        },
      );

      if (outcome.success) {
        if (outcome.result)
          set(uploaded, true);
      }
      else if (isActionableFailure(outcome)) {
        set(errorMessage, outcome.message);
      }
    }
  }
}

function changeShouldCustomDateFormat() {
  if (!isDefined(dateInputFormat))
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
  else set(dateInputFormat, undefined);
}

const isRotkiCustomImport = computed<boolean>(() => source.startsWith('rotki_'));
</script>

<template>
  <div :data-cy="`import-source-${source}`">
    <div class="mb-2">
      <slot name="upload-title" />
    </div>
    <form
      novalidate
      @submit.stop.prevent="uploadFile()"
    >
      <FileUpload
        v-model="file"
        v-model:error-message="errorMessage"
        :loading="loading"
        :uploaded="uploaded"
        :source="source"
        @update:uploaded="uploaded = $event"
      />
      <RuiSwitch
        v-if="!isRotkiCustomImport"
        color="primary"
        class="mt-4"
        :model-value="dateInputFormat !== undefined"
        @update:model-value="changeShouldCustomDateFormat()"
      >
        {{ t('file_upload.date_input_format.switch_label') }}
      </RuiSwitch>
      <RuiTextField
        v-if="dateInputFormat !== undefined"
        v-model="dateInputFormat"
        class="mt-2"
        variant="outlined"
        color="primary"
        :error-messages="toMessages(v$.dateInputFormat)"
        :label="t('file_upload.date_input_format.placeholder')"
        :hint="
          t('file_upload.date_input_format.hint', {
            format: dateInputFormatExample,
          })
        "
      >
        <template #append>
          <RuiButton
            variant="text"
            icon
            class="!p-2"
            @click="formatHelp = true"
          >
            <RuiIcon name="lu-info" />
          </RuiButton>
        </template>
      </RuiTextField>

      <div class="mt-4 text-sm leading-7 text-rui-text-secondary">
        <slot />
        <div v-if="$slots.hint">
          <slot name="hint" />
        </div>
      </div>
      <div class="mt-6">
        <RuiButton
          color="primary"
          class="w-full"
          data-cy="button-import"
          size="lg"
          type="submit"
          :disabled="v$.$invalid || !file || loading"
        >
          <template #prepend>
            <RuiIcon
              name="lu-file-up"
              size="18"
            />
          </template>
          {{ t('common.actions.import') }}
        </RuiButton>
      </div>
    </form>
    <DateFormatHelp v-model="formatHelp" />
  </div>
</template>
