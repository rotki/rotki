import type { AdditionSummary } from '@/modules/accounts/use-account-addition-service';
import type { GnosisPaySafeMigration, GnosisPayUntrackedSafe } from '@/modules/integrations/gnosis-pay/types';
import { pipe } from 'plainfp';
import { fromNullable, none, type Option } from 'plainfp/option';
import { err, ok, type Result } from 'plainfp/result';
import { fromAsync, map, type ResultAsync } from 'plainfp/result-async';
import { errorOf } from '@/modules/core/tasks/task-result';

/** What looking for an untracked Safe needs from the app. */
export interface SafeMigrationPorts {
  /** Whether a Gnosis Pay key is saved, loading the keys first when they are not loaded yet. */
  isConfigured: () => Promise<boolean>;
  fetchMigration: () => Promise<GnosisPaySafeMigration>;
}

/**
 * The Safe the Gnosis Pay migration left untracked, if any.
 *
 * @remarks
 * Skips the request unless Gnosis Pay is configured: it is premium-gated, and a user who does not
 * use the service would otherwise be told about a premium requirement for it. A failed request is
 * handed back rather than logged, since not being premium fails it too.
 */
export async function findUntrackedSafe(ports: SafeMigrationPorts): ResultAsync<Option<GnosisPayUntrackedSafe>, unknown> {
  if (!await ports.isConfigured())
    return ok(none);

  return pipe(
    fromAsync(ports.fetchMigration, (cause: unknown) => cause),
    map(migration => fromNullable(migration.untrackedAddresses[0])),
  );
}

/**
 * Reads what adding the Safe came to: `true` once it is added, `false` when there is nothing to
 * report, and the failure's message when it failed.
 *
 * @remarks
 * Nothing is reported for a cancellation, which the user asked for, or for a skip, which the task
 * dock already explains.
 */
export function readSafeAddition(summary: AdditionSummary): Result<boolean, string> {
  if (summary.added.length > 0)
    return ok(true);

  if (summary.failed.length > 0)
    return err(errorOf(summary.failed[0].error).message);

  return ok(false);
}
