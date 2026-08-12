import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toPeriodField } from '@/modules/core/table/filters/shared/period-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { InternalTxConflictFilterKeys } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts-filter';

type Translate = (key: string) => string;

/**
 * The pill-bar fields for the internal transaction conflicts table: the chain a conflict is on,
 * drawn as the shared chain pill, plus the two date bounds folded into one `period` pill. The wire
 * form is unchanged — the bounds still serialize to `fromTimestamp`/`toTimestamp`.
 *
 * The chain field is declared here rather than in `filters/shared/`: it is the only filter-bag chain
 * field so far (the address book's rides a param), so there is no second call site to shape a shared
 * builder from yet.
 */
export function toInternalTxConflictFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  chains: () => string[],
): FieldDef[] {
  return [
    decorateSharedField(
      toMatchFieldDef({
        key: InternalTxConflictFilterKeys.CHAIN,
        // The pill says what the column says.
        label: (): string => t('internal_tx_conflicts.columns.chain'),
        multiple: false,
        suggest: chains,
        // Checked against the same list it offers, so a chain the backend does not know is never
        // applied.
        validate: (value: string): boolean => chains().includes(value),
      }),
      SharedFieldKinds.CHAIN,
      resolvers,
    ),
    toPeriodField(
      (): string => t('internal_tx_conflicts.filter.period'),
      {
        lowerKey: InternalTxConflictFilterKeys.FROM_TIMESTAMP,
        upperKey: InternalTxConflictFilterKeys.TO_TIMESTAMP,
      },
      resolvers,
    ),
  ];
}
