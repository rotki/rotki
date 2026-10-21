<script setup lang="ts">
import type { ImportSourceType } from '@/modules/core/common/upload-types';
import { RuiFileUpload } from '@rotki/ui-library';
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
import ImportNotes from '@/modules/user-data/ImportNotes.vue';
import { useImportDataApi } from '@/modules/user-data/use-import-data-api';

const { source, notes = true } = defineProps<{
  source: ImportSourceType;
  /** Off for a source that splits into several uploads and shows its notes once, beside all of them. */
  notes?: boolean;
}>();

defineSlots<{
  'default'?: () => any;
  'hint'?: () => any;
  'upload-title': () => any;
}>();

interface ImportState {
  dateInputFormat: string | undefined;
}

const uploader = useTemplateRef<InstanceType<typeof RuiFileUpload>>('uploader');
const useCustomTimezone = ref<boolean>(false);
const optionsOpen = ref<boolean>(false);
const optionsId = useId();
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

/**
 * An import only counts as done when the task both settled and reported a completed import.
 *
 * @remarks
 * A completed import empties the uploader through its own `removeFile`, which also resets the
 * hidden input, so the same file cannot be imported twice by accident yet can still be picked
 * again on purpose. A failure keeps the file, so the parsing options can be changed and retried.
 *
 * @param outcome - what the import task settled on
 * @returns whether the import completed
 */
function applyOutcome(outcome: Result<boolean, TaskError>): boolean {
  if (!isErr(outcome)) {
    if (outcome.value) {
      get(uploader)?.removeFile();
      set(uploaded, true);
    }

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
    userStarted: true,
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
    userStarted: true,
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

/**
 * Drops the last import's outcome once another file is picked, so it is never shown beside a
 * file it was not about.
 *
 * @param picked - the uploader's new value, empty when the file was removed rather than picked
 */
function onFileChange(picked: File | File[] | undefined): void {
  if (!picked)
    return;

  set(uploaded, false);
  set(errorMessage, '');
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

// every third-party source carries the caveat that its format may change, even with no notes of its own
const showNotes = computed<boolean>(() => notes && !get(isRotkiCustomImport));

// counted on the collapsed toggle, so an option still in effect is never out of sight
const activeOptions = computed<number>(() =>
  (form.state.dateInputFormat === undefined ? 0 : 1) + (get(useCustomTimezone) ? 1 : 0),
);
</script>

<template>
  <div
    data-testid="import-source"
    :data-key="source"
    class="grid items-start gap-4"
    :class="{ 'lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]': showNotes }"
  >
    <form
      novalidate
      class="flex flex-col gap-4 rounded-rui-card border border-rui-divider bg-rui-surface p-4"
      @submit.stop.prevent="form.submit()"
    >
      <div
        v-if="$slots['upload-title']"
        class="text-sm text-rui-text"
      >
        <slot name="upload-title" />
      </div>
      <div class="flex flex-col gap-1">
        <RuiFileUpload
          ref="uploader"
          v-model="file"
          accept=".csv"
          details="hidden"
          :loading="loading"
          :uploaded="uploaded"
          :error-messages="errorMessage ? [errorMessage] : []"
          :upload-text="t('file_upload.dropzone.prefix')"
          :click-to-upload-text="t('file_upload.dropzone.choose')"
          :replace-text="t('file_upload.dropzone.replace')"
          data-testid="import-file-upload"
          @error="errorMessage = $event"
          @update:model-value="onFileChange($event)"
        />
        <div
          v-if="errorMessage"
          class="min-h-5 text-sm text-rui-error"
          data-testid="import-error"
        >
          {{ errorMessage }}
        </div>
        <div
          v-else-if="uploaded"
          class="flex min-h-5 items-center gap-1.5 text-sm text-rui-success"
          data-testid="import-complete"
        >
          <RuiIcon
            name="lu-circle-check"
            size="14"
          />
          {{ t('file_upload.import_complete') }}
        </div>
        <div
          v-else
          class="min-h-5"
        />
      </div>
      <div class="flex flex-wrap items-center gap-x-4 gap-y-3">
        <RuiButton
          v-if="!isRotkiCustomImport"
          variant="text"
          size="sm"
          class="-ml-1.5"
          :color="activeOptions > 0 ? 'primary' : undefined"
          :aria-expanded="optionsOpen"
          :aria-controls="optionsId"
          data-testid="import-options-toggle"
          @click="optionsOpen = !optionsOpen"
        >
          <template #prepend>
            <RuiIcon
              name="lu-settings-2"
              size="16"
            />
          </template>
          {{
            activeOptions > 0 && !optionsOpen
              ? t('import_data.parsing_options_active', { count: activeOptions })
              : t('import_data.parsing_options')
          }}
          <template #append>
            <RuiIcon
              :name="optionsOpen ? 'lu-chevron-up' : 'lu-chevron-down'"
              size="16"
            />
          </template>
        </RuiButton>

        <RuiButton
          color="primary"
          class="ml-auto"
          data-testid="button-import"
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

        <div
          v-if="!isRotkiCustomImport && optionsOpen"
          :id="optionsId"
          class="flex basis-full flex-col gap-3"
        >
          <RuiSwitch
            color="primary"
            details="hidden"
            :model-value="form.state.dateInputFormat !== undefined"
            data-testid="import-date-format-switch"
            @update:model-value="changeShouldCustomDateFormat()"
          >
            {{ t('file_upload.date_input_format.switch_label') }}
          </RuiSwitch>
          <RuiTextField
            v-if="form.state.dateInputFormat !== undefined"
            v-model="form.state.dateInputFormat"
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
                class="p-2!"
                @click="formatHelp = true"
              >
                <RuiIcon name="lu-info" />
              </RuiButton>
            </template>
          </RuiTextField>

          <div data-testid="import-timezone-switch">
            <RuiSwitch
              color="primary"
              details="hidden"
              :model-value="useCustomTimezone"
              @update:model-value="toggleCustomTimezone($event)"
            >
              {{ t('file_upload.timezone.switch_label') }}
            </RuiSwitch>
          </div>
          <div
            v-if="useCustomTimezone"
            data-testid="import-timezone-select"
          >
            <RuiTimezoneSelect
              v-model="timezone"
              clearable
              :label="t('file_upload.timezone.label')"
              :hint="t('file_upload.timezone.hint')"
            />
          </div>
        </div>
      </div>
    </form>

    <ImportNotes v-if="showNotes">
      <template
        v-if="$slots.default || $slots.hint"
        #default
      >
        <slot />
        <div
          v-if="$slots.hint"
          class="mt-2"
        >
          <slot name="hint" />
        </div>
      </template>
    </ImportNotes>
    <DateFormatHelp
      v-model="formatHelp"
      class="hidden"
    />
  </div>
</template>
