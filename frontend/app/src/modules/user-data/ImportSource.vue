<script setup lang="ts">
import type { ImportSourceType } from '@/modules/core/common/upload-types';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';
import { DateFormat } from '@/modules/core/common/date-format';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { useForm } from '@/modules/core/form/use-form';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import DateFormatHelp from '@/modules/settings/controls/DateFormatHelp.vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import FileUpload from '@/modules/user-data/FileUpload.vue';
import { useImportDataApi } from '@/modules/user-data/use-import-data-api';

const { source } = defineProps<{ source: ImportSourceType }>();

defineSlots<{
  'default': () => any;
  'hint': () => any;
  'upload-title': () => any;
}>();

interface ImportState {
  dateInputFormat: string | undefined;
}

const useCustomTimezone = ref<boolean>(false);
const timezone = ref<string>();
const uploaded = ref(false);
const errorMessage = ref('');
const formatHelp = ref<boolean>(false);
const file = ref<File>();

const { t } = useI18n({ useScope: 'global' });
const { getPath } = useInterop();

/**
 * The empty-value rule only ever fires on a pattern that is truthy but blank once trimmed, because
 * vuelidate armed it with `requiredIf(refIsTruthy(self))` and then trimmed before checking. A field
 * cleared to '' therefore reports only the invalid-pattern message, which is preserved here.
 */
const schema = computed<ZodType>(() => z.object({
  dateInputFormat: z.string().optional().superRefine((value, ctx) => {
    if (value === undefined)
      return;

    if (value !== '' && value.trim() === '')
      ctx.addIssue({ code: 'custom', message: t('general_settings.date_display.validation.empty') });

    if (!displayDateFormatter.containsValidDirectives(value))
      ctx.addIssue({ code: 'custom', message: t('general_settings.date_display.validation.invalid') });
  }),
}));

const form = useForm<ImportState, ImportState>({
  initial: (): ImportState => ({ dateInputFormat: undefined }),
  schema,
  submit: async (): Promise<{ success: boolean }> => ({ success: await uploadFile() }),
  transform: (state): ImportState => ({ dateInputFormat: state.dateInputFormat }),
});

// Destructured, because a ref reached through `form.` in the template is not unwrapped and would
// read as permanently truthy.
const { valid } = form;

const dateInputFormatExample = computed<string>(() => {
  const format = form.state.dateInputFormat;
  if (!format)
    return '';

  return displayDateFormatter.format(new Date(), format);
});

const { submitTask } = useNativeTask();
const { useIsActive } = useTaskCenter();

const loading = useIsActive(ActivityKind.CSV_IMPORT, source);
const { importDataFrom, importFile } = useImportDataApi();

/** An import only counts as done when the task both settled and reported a completed import. */
function applyOutcome(outcome: Result<boolean, TaskError>): boolean {
  if (!isErr(outcome)) {
    if (outcome.value)
      set(uploaded, true);

    return outcome.value;
  }

  if (isActionable(outcome.error))
    set(errorMessage, outcome.error.message);

  return false;
}

async function uploadPackaged(file: string): Promise<boolean> {
  const outcome = await submitTask<boolean>({
    id: makeActivityId(ActivityKind.CSV_IMPORT, source),
    kind: ActivityKind.CSV_IMPORT,
    rerunnable: false,
    run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
      await runTask<boolean>(
        () => importDataFrom({
          file,
          source,
          timestampFormat: form.state.dateInputFormat || null,
          timezone: get(timezone) || null,
        }),
      ),
      value => value,
    ),
    subtitle: activityLabelFor(msg.$t('task_center.activity.csv_import.source'), { source }),
    title: t('task_center.group.csv_import'),
  });

  return applyOutcome(outcome);
}

async function uploadFile(): Promise<boolean> {
  const fileVal = get(file);
  if (!fileVal)
    return false;

  const path = getPath(fileVal);
  if (path)
    return uploadPackaged(path);

  const formData = new FormData();
  formData.append('source', source);
  formData.append('file', fileVal);
  formData.append('async_query', 'true');
  const dateInputFormatVal = form.state.dateInputFormat;
  if (dateInputFormatVal)
    formData.append('timestamp_format', dateInputFormatVal);
  const timezoneVal = get(timezone);
  if (timezoneVal)
    formData.append('timezone', timezoneVal);

  const outcome = await submitTask<boolean>({
    id: makeActivityId(ActivityKind.CSV_IMPORT, source),
    kind: ActivityKind.CSV_IMPORT,
    rerunnable: false,
    run: async ({ runTask }): Promise<Result<boolean, TaskError>> => mapResult(
      await runTask<boolean>(
        () => importFile(formData),
      ),
      value => value,
    ),
    subtitle: activityLabelFor(msg.$t('task_center.activity.csv_import.source'), { source }),
    title: t('task_center.group.csv_import'),
  });

  return applyOutcome(outcome);
}

function changeShouldCustomDateFormat(): void {
  form.state.dateInputFormat = form.state.dateInputFormat === undefined
    ? DateFormat.DateMonthYearHourMinuteSecond
    : undefined;
}

function toggleCustomTimezone(enabled: boolean): void {
  set(useCustomTimezone, enabled);
  if (!enabled)
    set(timezone, undefined);
}

const isRotkiCustomImport = computed<boolean>(() => source.startsWith('rotki_'));
</script>

<template>
  <div
    data-testid="import-source"
    :data-key="source"
  >
    <div class="mb-2">
      <slot name="upload-title" />
    </div>
    <form
      novalidate
      @submit.stop.prevent="form.submit()"
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
        :model-value="form.state.dateInputFormat !== undefined"
        data-testid="import-date-format-switch"
        @update:model-value="changeShouldCustomDateFormat()"
      >
        {{ t('file_upload.date_input_format.switch_label') }}
      </RuiSwitch>
      <RuiTextField
        v-if="form.state.dateInputFormat !== undefined"
        v-model="form.state.dateInputFormat"
        class="mt-2"
        variant="outlined"
        color="primary"
        :error-messages="form.errors('dateInputFormat')"
        data-testid="import-date-format"
        :label="t('file_upload.date_input_format.placeholder')"
        :hint="
          t('file_upload.date_input_format.hint', {
            format: dateInputFormatExample,
          })
        "
        @update:model-value="form.touch('dateInputFormat')"
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

      <div
        v-if="!isRotkiCustomImport"
        data-testid="import-timezone-switch"
      >
        <RuiSwitch
          color="primary"
          class="mt-4"
          :model-value="useCustomTimezone"
          @update:model-value="toggleCustomTimezone($event)"
        >
          {{ t('file_upload.timezone.switch_label') }}
        </RuiSwitch>
      </div>
      <div
        v-if="useCustomTimezone"
        data-testid="import-timezone-select"
        class="mt-2"
      >
        <RuiTimezoneSelect
          v-model="timezone"
          variant="outlined"
          clearable
          :label="t('file_upload.timezone.label')"
          :hint="t('file_upload.timezone.hint')"
        />
      </div>

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
          data-testid="button-import"
          size="lg"
          type="submit"
          :disabled="!valid || !file || loading"
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
