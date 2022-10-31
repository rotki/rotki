<template>
  <div>
    <div>
      <div class="mb-2">
        <slot name="upload-title" />
      </div>
      <v-form ref="form" v-model="valid">
        <file-upload
          :loading="loading"
          :uploaded="uploaded"
          :source="source"
          :error-message="errorMessage"
          @selected="upload($event)"
          @update:uploaded="uploaded = $event"
        />
        <v-switch
          v-if="!isRotkiCustomImport"
          :value="dateInputFormat !== null"
          @change="changeShouldCustomDateFormat"
        >
          <template #label>
            {{ t('file_upload.date_input_format.switch_label') }}
          </template>
        </v-switch>
        <v-text-field
          v-if="dateInputFormat !== null"
          v-model="dateInputFormat"
          class="mt-2"
          outlined
          :rules="dateFormatRules"
          :placeholder="t('file_upload.date_input_format.placeholder')"
          :hint="
            t('file_upload.date_input_format.hint', {
              format: dateInputFormatExample
            })
          "
          persistent-hint
        >
          <template #append>
            <v-btn small icon @click="formatHelp = true">
              <v-icon small> mdi-information </v-icon>
            </v-btn>
          </template>
        </v-text-field>

        <div class="mt-4">
          <v-row>
            <v-col cols="12">
              <slot />
            </v-col>
          </v-row>
          <v-row v-if="$slots.hint">
            <v-col cols="12">
              <slot name="hint" />
            </v-col>
          </v-row>
        </div>
        <div class="mt-6">
          <v-btn
            color="primary"
            depressed
            block
            data-cy="button-import"
            :disabled="!valid || !file || loading"
            @click="uploadFile"
          >
            {{ t('common.actions.import') }}
          </v-btn>
        </div>
      </v-form>
    </div>
    <date-format-help v-model="formatHelp" />
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import FileUpload from '@/components/import/FileUpload.vue';
import DateFormatHelp from '@/components/settings/controls/DateFormatHelp.vue';
import { displayDateFormatter } from '@/data/date_formatter';
import { interop } from '@/electron-interop';
import { api } from '@/services/rotkehlchen-api';
import { useTasks } from '@/store/tasks';
import { DateFormat } from '@/types/date-format';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { ImportSourceType } from '@/types/upload-types';

const props = defineProps({
  icon: {
    required: false,
    default: '',
    type: String
  },
  source: { required: true, type: String as PropType<ImportSourceType> }
});

const { source } = toRefs(props);
const dateInputFormat = ref<string | null>(null);
const uploaded = ref(false);
const errorMessage = ref('');
const valid = ref<boolean>(true);
const formatHelp = ref<boolean>(false);
const file = ref<File | null>(null);

const { t } = useI18n();

const upload = (selectedFile: File) => {
  set(file, selectedFile);
};

const dateFormatRules = [
  (v: string) => {
    if (!v) {
      return t('general_settings.date_display.validation.empty');
    }
    if (!displayDateFormatter.containsValidDirectives(v)) {
      return t('general_settings.date_display.validation.invalid').toString();
    }
    return true;
  }
];

const dateInputFormatExample = computed(() => {
  const now = new Date();
  if (!get(dateInputFormat)) return '';
  return displayDateFormatter.format(now, get(dateInputFormat)!);
});

const taskType = TaskType.IMPORT_CSV;
const { awaitTask, isTaskRunning } = useTasks();

const loading = isTaskRunning(taskType, { source: get(source) });

const uploadPackaged = async (file: string) => {
  try {
    const sourceVal = get(source);
    const { taskId } = await api.importDataFrom(
      sourceVal,
      file,
      get(dateInputFormat) || null
    );

    const taskMeta = {
      title: t('file_upload.task.title', { source: sourceVal }).toString(),
      numericKeys: [],
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
  if (get(file)) {
    if (interop.isPackaged && api.defaultBackend) {
      await uploadPackaged(get(file)!.path);
    } else {
      const formData = new FormData();
      formData.append('source', get(source));
      formData.append('file', get(file)!);
      formData.append('async_query', 'true');
      if (get(dateInputFormat)) {
        formData.append('timestamp_format', get(dateInputFormat)!);
      }
      try {
        const { taskId } = await api.importFile(formData);
        const { result } = await awaitTask<boolean, TaskMeta>(
          taskId,
          taskType,
          {
            title: t('file_upload.task.title', {
              source: get(source)
            }).toString(),
            numericKeys: []
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

const isRotkiCustomImport = computed(() => {
  return get(source).startsWith('rotki_');
});
</script>

<style module lang="scss">
.image {
  padding: 10px;
  max-width: 200px;
}
</style>
