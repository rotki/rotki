import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef, ValueIcon } from '@/modules/core/table/pill/core/types';
import type { DataIssueAccountOptions } from '@/modules/history/data-issues/use-data-issue-account-options';
import { decorateSharedField, type SharedFieldKind, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toDateFieldDef, toFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { DataIssuesFilterValueKeys, type Matcher } from '@/modules/history/data-issues/use-data-issues-filter';

type Translate = (key: string) => string;

/**
 * How the two data-issue enums read on a pill. Both are machine values on the wire
 * (`auto_remediating`, `current_balance_mismatch`) that the table already draws as a labelled,
 * coloured chip, so the pill has to say the same thing rather than show the raw value.
 */
export interface DataIssueFieldResolution {
  /** The account pill's option list and how each account reads, resolved from the user's history. */
  readonly account: DataIssueAccountOptions;
  readonly resolveStateLabel: (value: string) => string;
  readonly resolveStateIcon: (value: string) => ValueIcon | undefined;
  readonly resolveKindLabel: (value: string) => string;
  readonly resolveKindIcon: (value: string) => ValueIcon | undefined;
}

// Only the asset is a shared kind here. The account is deliberately NOT the shared address kind:
// it carries a `locationLabel`, which is an address on a chain but an exchange account *name*
// everywhere else, and the table draws that name with its location icon and explicitly leaves it
// unscrambled (`HistoryEventAccount`). Scrambling it would mangle a name the app never scrambles,
// and a blockie beside it would claim it is an address. Its option list knows which of the two a
// value is, so it resolves per value (`resolveDisplay`): a blockie for an address, the exchange's
// own logo for an account held there, which is what the table draws too.
const sharedKinds: Partial<Record<string, SharedFieldKind>> = {
  [DataIssuesFilterValueKeys.ASSET]: SharedFieldKinds.ASSET,
};

/**
 * The pill-bar fields for the data issues table: the state, kind, asset and account matchers, plus
 * the two date matchers folded into one `period` pill, the way history and oracle prices do it. The
 * wire form is unchanged — the bounds still serialize to `fromTimestamp`/`toTimestamp`.
 */
export function toDataIssueFields(
  matchers: Matcher[],
  resolvers: SharedFieldResolvers,
  t: Translate,
  resolution: DataIssueFieldResolution,
): FieldDef[] {
  const { formatDate, parseDate } = resolvers;
  const result: FieldDef[] = [];

  for (const matcher of matchers) {
    const key = String(matcher.keyValue ?? matcher.key);

    if (key === DataIssuesFilterValueKeys.START) {
      // No serializer of its own: the two bounds are stored as the timestamps they are sent as, and
      // the date editor reads and writes them through `formatBound`/`parseBound`.
      result.push(toDateFieldDef({
        formatBound: formatDate,
        key: 'period',
        label: t('data_issues.filter.period'),
        lowerKey: DataIssuesFilterValueKeys.START,
        parseBound: parseDate,
        upperKey: DataIssuesFilterValueKeys.END,
      }));
      continue;
    }

    // The second bound of the collapsed pair is already represented by the pill above.
    if (key === DataIssuesFilterValueKeys.END)
      continue;

    const field = decorateSharedField(toFieldDef(matcher), sharedKinds[key], resolvers);

    if (key === DataIssuesFilterValueKeys.STATE) {
      result.push({
        ...field,
        resolveIcon: resolution.resolveStateIcon,
        resolveLabel: resolution.resolveStateLabel,
      });
      continue;
    }

    if (key === DataIssuesFilterValueKeys.ACCOUNT) {
      // Picked, not written: the matcher offers no suggestions of its own, but the accounts an
      // issue can name are exactly the location labels the user's history has, which is the same
      // list history's account pill picks from. The endpoint takes one label, so `multiple` stays
      // as the matcher declared it.
      result.push({ ...field, ...resolution.account });
      continue;
    }

    if (key === DataIssuesFilterValueKeys.KIND) {
      result.push({
        ...field,
        resolveIcon: resolution.resolveKindIcon,
        resolveLabel: resolution.resolveKindLabel,
      });
      continue;
    }

    result.push(field);
  }

  return result;
}
