import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/**
 * Generating a PnL report.
 *
 * @remarks
 * Its id is the bare kind, so `partsOf()` is empty. A status read with no parts aggregates the
 * whole kind; the report page reads it that way on purpose, since an export and a debug import poll
 * the same report progress and show the same progress screen. Only a lookup by id, such as the
 * page's `useActivity`, reads generation alone.
 */
export const pnlReportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.PNL_REPORT,
});

/** Exporting a report's data. */
export const pnlReportExportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.PNL_REPORT,
  part: ActivityPart.EXPORT,
});

/** Importing report data for debugging. */
export const pnlReportImportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.PNL_REPORT,
  part: ActivityPart.IMPORT,
});
