<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import { displayDateFormatter } from '@/data/date_formatter';
import { DateFormat } from '@/types/date-format';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type ImportSourceType } from '@/types/upload-types';

const props = withDefaults(
  defineProps<{ source: ImportSourceType; icon?: string }>(),
  { icon: '' }
);

const { source } = toRefs(props);
const dateInputFormat = ref<string | null>(null);
const uploaded = ref(false);
const errorMessage = ref('');
const formatHelp = ref<boolean>(false);
const file = ref<File | null>(null);

const { t } = useI18n();
const { appSession } = useInterop();

const rules = {
  dateInputFormat: {
    required: helpers.withMessage(
      t('general_settings.date_display.validation.empty').toString(),
      requiredIf(refIsTruthy(dateInputFormat))
    ),
    validDate: helpers.withMessage(
      t('general_settings.date_display.validation.invalid').toString(),
      (v: string | null): boolean =>
        v === null || displayDateFormatter.containsValidDirectives(v)
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    dateInputFormat
  },
  { $autoDirty: true }
);

const dateInputFormatExample = computed(() => {
  const now = new Date();
  if (!get(dateInputFormat)) {
    return '';
  }
  return displayDateFormatter.format(now, get(dateInputFormat)!);
});

const taskType = TaskType.IMPORT_CSV;
const { awaitTask, isTaskRunning } = useTaskStore();

const loading = isTaskRunning(taskType, { source: get(source) });
const { importDataFrom, importFile } = useImportDataApi();

const uploadPackaged = async (file: string) => {
  try {
    const sourceVal = get(source);
    const { taskId } = await importDataFrom(
      sourceVal,
      file,
      get(dateInputFormat) || null
    );

    const taskMeta = {
      title: t('file_upload.task.title', { source: sourceVal }).toString(),
      source: sourceVal
    };

    const { result } = await awaitTask<boolean, TaskMeta>(
      taskId,
      taskType,
      taskMeta,
      true
    );

    if (result) {
      set(uploaded, true);
    }
  } catch (e: any) {
    set(errorMessage, e.message);
  }
};

const uploadFile = async () => {
  const fileVal = get(file);
  if (fileVal) {
    if (appSession) {
      await uploadPackaged(fileVal.path);
    } else {
      const formData = new FormData();
      formData.append('source', get(source));
      formData.append('file', fileVal);
      formData.append('async_query', 'true');
      const dateInputFormatVal = get(dateInputFormat);
      if (dateInputFormatVal) {
        formData.append('timestamp_format', dateInputFormatVal);
      }
      try {
        const { taskId } = await importFile(formData);
        const { result } = await awaitTask<boolean, TaskMeta>(
          taskId,
          taskType,
          {
            title: t('file_upload.task.title', {
              source: get(source)
            }).toString()
          }
        );

        if (result) {
          set(uploaded, true);
        }
      } catch (e: any) {
        set(errorMessage, e.message);
      }
    }
  }
};

const changeShouldCustomDateFormat = () => {
  if (get(dateInputFormat) === null) {
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
  } else {
    set(dateInputFormat, null);
  }
};

const isRotkiCustomImport = computed(() => get(source).startsWith('rotki_'));
</script>

<template>
  <div>
    <div class="mb-2">
      <slot name="upload-title" />
    </div>
    <form>
      <FileUpload
        v-model="file"
        :loading="loading"
        :uploaded="uploaded"
        :source="source"
        :error-message="errorMessage"
        @update:uploaded="uploaded = $event"
      />
      <VSwitch
        v-if="!isRotkiCustomImport"
        :value="dateInputFormat !== null"
        @change="changeShouldCustomDateFormat()"
      >
        <template #label>
          {{ t('file_upload.date_input_format.switch_label') }}
        </template>
      </VSwitch>
      <RuiTextField
        v-if="dateInputFormat !== null"
        v-model="dateInputFormat"
        class="mt-2"
        variant="outlined"
        color="primary"
        :error-messages="v$.dateInputFormat.$errors.map(e => e.$message)"
        :label="t('file_upload.date_input_format.placeholder')"
        :hint="
          t('file_upload.date_input_format.hint', {
            format: dateInputFormatExample
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
            <RuiIcon name="information-line" />
          </RuiButton>
        </template>
      </RuiTextField>

      <div class="mt-4">
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
          :disabled="v$.$invalid || !file || loading"
          @click="uploadFile()"
        >
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
