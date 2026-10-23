import type { ImportSourceType } from '@/modules/core/common/upload-types';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind } from '@/modules/task-center/core/types';

/** One import, keyed by its source so imports from two sources run side by side. */
export const csvImportActivity = defineActivity<{ source: ImportSourceType }, readonly [ImportSourceType]>({
  key: subject => [subject.source],
  kind: ActivityKind.CSV_IMPORT,
});
