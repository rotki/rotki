import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef, ValueIcon } from '@/modules/core/table/pill/core/types';
import type { DataIssueAccountOptions } from '@/modules/history/data-issues/use-data-issue-account-options';
import { toAssetField } from '@/modules/core/table/filters/shared/asset-field';
import { toPeriodField } from '@/modules/core/table/filters/shared/period-field';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { IssueKind, IssueState } from '@/modules/history/data-issues/constants';
import { DataIssuesFilterKeys } from '@/modules/history/data-issues/use-data-issues-filter';

type Translate = (key: string) => string;

/**
 * How the two data-issue enums read on a pill. Both are machine values on the wire
 * (`auto_remediating`, `current_balance_mismatch`) that the table already draws as a labelled,
 * coloured chip, so the pill has to say the same thing rather than show the raw value.
 */
export interface DataIssueFieldResolution {
  /** The account pill's option list and how each account reads, resolved from the user's history. */
  readonly account: DataIssueAccountOptions;
  /** The async asset search backing the asset picker. */
  readonly searchAsset: (value: string) => Promise<AssetsWithId>;
  readonly resolveStateLabel: (value: string) => string;
  readonly resolveStateIcon: (value: string) => ValueIcon | undefined;
  readonly resolveKindLabel: (value: string) => string;
  readonly resolveKindIcon: (value: string) => ValueIcon | undefined;
}

const STATES: string[] = Object.values(IssueState);
const KINDS: string[] = Object.values(IssueKind);

/**
 * The pill-bar fields for the data issues table: the state, kind, asset and account, plus the two
 * date bounds folded into one `period` pill, the way history and oracle prices do it. The wire form
 * is unchanged — the bounds still serialize to `fromTimestamp`/`toTimestamp`.
 */
export function toDataIssueFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  resolution: DataIssueFieldResolution,
): FieldDef[] {
  return [
    toMatchFieldDef({
      key: DataIssuesFilterKeys.STATE,
      label: (): string => t('data_issues.filter.state'),
      multiple: true,
      resolveIcon: resolution.resolveStateIcon,
      resolveLabel: resolution.resolveStateLabel,
      suggest: (): string[] => STATES,
      validate: (value: string): boolean => STATES.includes(value),
    }),
    toMatchFieldDef({
      key: DataIssuesFilterKeys.KIND,
      label: (): string => t('data_issues.filter.kind'),
      multiple: true,
      resolveIcon: resolution.resolveKindIcon,
      resolveLabel: resolution.resolveKindLabel,
      suggest: (): string[] => KINDS,
      validate: (value: string): boolean => KINDS.includes(value),
    }),
    toAssetField({
      key: DataIssuesFilterKeys.ASSET,
      label: (): string => t('data_issues.filter.asset'),
      searchAsset: resolution.searchAsset,
    }, resolvers),
    {
      // Not the shared address kind: a `locationLabel` is an address on a chain but an exchange
      // account *name* elsewhere, so `resolveDisplay` decides per value.
      ...toMatchFieldDef({
        key: DataIssuesFilterKeys.ACCOUNT,
        label: (): string => t('data_issues.filter.account'),
        multiple: false,
        // Not checked against the option list: it is fetched as the bar is built, so a value
        // restored from the URL can arrive first.
        validate: (value: string): boolean => value.length > 0,
      }),
      ...resolution.account,
    },
    toPeriodField(
      (): string => t('data_issues.filter.period'),
      { lowerKey: DataIssuesFilterKeys.START, upperKey: DataIssuesFilterKeys.END },
      resolvers,
    ),
  ];
}
