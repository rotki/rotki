import type { ImportSourceType } from '@/modules/core/common/upload-types';
import type { useImportLocationMapping } from '@/modules/user-data/use-import-location-mapping';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { useI18n } from 'vue-i18n';
import { z } from 'zod';
import { msg } from '@/message-key';
import { Cancelled, Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { csvImportActivity } from '@/modules/user-data/csv-import.activity';
import { useImportDataApi } from '@/modules/user-data/use-import-data-api';

type CheckLocations = ReturnType<typeof useImportLocationMapping>['checkLocations'];

interface UseCsvImportTaskOptions {
  /** The source the file is imported as, which also keys the activity. */
  source: MaybeRefOrGetter<ImportSourceType>;
  /** Checks how the file's location values resolve, before a rotki generic import goes ahead. */
  checkLocations: CheckLocations;
}

interface CsvImportPayload {
  /** The CSV file the user picked. */
  readonly file: File;
  /** The location the user chose for each value that did not resolve. */
  readonly locationMappings: Record<string, string>;
  /** The date format the file's timestamps are in, or null for the default one. */
  readonly timestampFormat: string | null;
  /** The timezone the file's timestamps are in, or null for the default one. */
  readonly timezone: string | null;
}

interface UseCsvImportTaskReturn {
  /** Whether an import of this source is running. */
  readonly loading: ComputedRef<boolean>;
  /**
   * Imports one CSV file as a task center activity.
   *
   * @returns whether the backend reported a completed import, or why the task did not settle
   */
  readonly importCsv: (payload: CsvImportPayload) => Promise<Result<boolean, TaskError>>;
}

/**
 * Runs a CSV import as a task center activity, by path when the app can read the file from disk
 * and as an upload otherwise.
 */
export function useCsvImportTask({ checkLocations, source }: UseCsvImportTaskOptions): UseCsvImportTaskReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getPath } = useInterop();
  const { submitTask } = useNativeTask();
  const { useIsActive } = useTaskCenter();
  const { importDataFrom, importFile } = useImportDataApi();

  const loading = useIsActive(csvImportActivity.kind, ...csvImportActivity.partsOf({ source: toValue(source) }));

  async function importCsv({ file, locationMappings, timestampFormat, timezone }: CsvImportPayload): Promise<Result<boolean, TaskError>> {
    const sourceVal = toValue(source);
    const path = getPath(file);
    const payload = {
      file: path,
      locationMappings,
      source: sourceVal,
      timestampFormat,
      timezone,
    };
    const formData = new FormData();
    formData.append('source', sourceVal);
    formData.append('file', file);
    formData.append('location_mappings', JSON.stringify(locationMappings));
    if (payload.timestampFormat)
      formData.append('timestamp_format', payload.timestampFormat);
    if (payload.timezone)
      formData.append('timezone', payload.timezone);

    return submitTask<boolean>({
      id: csvImportActivity.id({ source: sourceVal }),
      kind: csvImportActivity.kind,
      rerunnable: false,
      userStarted: true,
      run: async ({ cancelled, runTask }): Promise<Result<boolean, TaskError>> => {
        if (sourceVal === 'rotki_events' || sourceVal === 'rotki_trades') {
          const check = await checkLocations(sourceVal, path ? { path } : { formData });
          if (check === 'unplaced')
            return err(Skipped({ message: t('import_data.location_mapping.skipped') }));
          if (check === 'replaced' || cancelled())
            return err(Cancelled({ message: 'cancelled' }));
        }

        formData.append('async_query', 'true');
        const result = await runTask<unknown>(async () => path ? importDataFrom({ ...payload, file: path }) : importFile(formData));
        if (isErr(result))
          return result;

        return ok(z.boolean().parse(result.value));
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.csv_import.source'), { source: sourceVal }),
      title: t('task_center.group.csv_import'),
    });
  }

  return { importCsv, loading };
}
