import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** Exporting the accounting rules to a file. */
export const accountingRulesExportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ACCOUNTING_RULES,
  part: ActivityPart.EXPORT,
});

/** Importing accounting rules from a file. */
export const accountingRulesImportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ACCOUNTING_RULES,
  part: ActivityPart.IMPORT,
});

/** Resetting the accounting rules to their defaults. */
export const accountingRulesResetActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ACCOUNTING_RULES,
  part: ActivityPart.RESET,
});
