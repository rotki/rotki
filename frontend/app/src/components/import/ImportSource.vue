<script setup lang="ts">
import type { TaskMeta } from '@/types/task';
import type { ImportSourceType } from '@/types/upload-types';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import FileUpload from '@/components/import/FileUpload.vue';
import DateFormatHelp from '@/components/settings/controls/DateFormatHelp.vue';
import { useImportDataApi } from '@/composables/api/import';
import { useInterop } from '@/composables/electron-interop';
import { refIsTruthy } from '@/composables/ref';
import { displayDateFormatter } from '@/data/date-formatter';
import { useTaskStore } from '@/store/tasks';
import { DateFormat } from '@/types/date-format';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { toMessages } from '@/utils/validation';

const props = withDefaults(defineProps<{ source: ImportSourceType; icon?: string }>(), { icon: '' });

defineSlots<{
  'default': () => any;
  'hint': () => any;
  'upload-title': () => any;
}>();

const { source } = toRefs(props);
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
const { awaitTask, useIsTaskRunning } = useTaskStore();

const loading = useIsTaskRunning(taskType, { source: get(source) });
const { importDataFrom, importFile } = useImportDataApi();

async function uploadPackaged(file: string) {
  try {
    const sourceVal = get(source);
    const { taskId } = await importDataFrom(sourceVal, file, get(dateInputFormat) || null);

    const taskMeta = {
      source: sourceVal,
      title: t('file_upload.task.title', { source: sourceVal }),
    };

    const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);

    if (result)
      set(uploaded, true);
  }
  catch (error: any) {
    if (!isTaskCancelled(error))
      set(errorMessage, error.message);
  }
}

async function uploadFile() {
  const fileVal = get(file);
  if (fileVal) {
    const path = getPath(fileVal);
    if (path) {
      await uploadPackaged(path);
    }
    else {
      const formData = new FormData();
      formData.append('source', get(source));
      formData.append('file', fileVal);
      formData.append('async_query', 'true');
      const dateInputFormatVal = get(dateInputFormat);
      if (dateInputFormatVal)
        formData.append('timestamp_format', dateInputFormatVal);

      try {
        const { taskId } = await importFile(formData);
        const taskMeta = {
          source: get(source),
          title: t('file_upload.task.title', { source: get(source) }),
        };
        const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta);

        if (result)
          set(uploaded, true);
      }
      catch (error: any) {
        if (!isTaskCancelled(error))
          set(errorMessage, error.message);
      }
    }
  }
}

function changeShouldCustomDateFormat() {
  if (!isDefined(dateInputFormat))
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
  else set(dateInputFormat, undefined);
}

const isRotkiCustomImport = computed(() => get(source).startsWith('rotki_'));
</script>

<template>
  <div>
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

<style module lang="scss">
.image {
  padding: 10px;
  max-width: 200px;
}
</style>
