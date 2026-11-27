import type { Ref, WritableComputedRef } from 'vue';
import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { DataIssueAccountOptions } from '@/modules/history/data-issues/use-data-issue-account-options';
import { AccountHistoryQueryKeys } from '@/modules/balances/account-history/account-history-selection';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { optionalStringParam, type PillParams, toPillParams } from '@/modules/core/table/param-refs';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';

type Translate = (key: string) => string;

/** What the fields need from the Vue layer to be built. */
export interface AccountHistoryFieldOptions {
  /** Every account the user's history has, and how each reads. */
  readonly accounts: DataIssueAccountOptions;
  /** The assets the picked account has held; absent when they cannot be listed, so any asset is searched. */
  readonly assets: (() => string[]) | undefined;
  /** The async search over every asset, used when `assets` is absent. */
  readonly searchAsset: (value: string) => Promise<AssetsWithId>;
  /** The locations the account held the asset in; absent when the balances are not loaded, so no location pill is offered. */
  readonly locations: (() => string[]) | undefined;
}

/**
 * The pill-bar fields for the account history page: the one account and the one asset it charts,
 * and optionally one location to narrow them to.
 *
 * Both are single-valued and param-bound to the page's selection, which lives in the route query,
 * so a pill is exactly what the url says. The asset offers only what the account has held when
 * that list is known (premium), as a list the shared asset decoration draws with icons, and
 * otherwise searches every asset.
 */
export function toAccountHistoryFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: AccountHistoryFieldOptions,
): FieldDef[] {
  const { accounts, assets, locations, searchAsset } = options;
  const location = locations
    ? [decorateSharedField(
        toParamFieldDef({
          key: AccountHistoryQueryKeys.LOCATION,
          label: (): string => t('common.location'),
          multiple: false,
          paramKey: AccountHistoryQueryKeys.LOCATION,
          suggest: locations,
          to: 'both',
        }),
        SharedFieldKinds.LOCATION,
        resolvers,
      )]
    : [];
  return [
    {
      ...toParamFieldDef({
        display: DisplayKinds.ACCOUNT,
        key: AccountHistoryQueryKeys.ACCOUNT,
        label: (): string => t('account_history.selectors.account'),
        multiple: false,
        paramKey: AccountHistoryQueryKeys.ACCOUNT,
        resolveCaption: accounts.resolveCaption,
        resolveKeywords: accounts.resolveKeywords,
        resolveLabel: accounts.resolveLabel,
        resolveLoading: accounts.resolveLoading,
        suggest: accounts.suggest,
        to: 'both',
      }),
      resolveDisplay: accounts.resolveDisplay,
    },
    decorateSharedField(
      toParamFieldDef({
        key: AccountHistoryQueryKeys.ASSET,
        label: (): string => t('account_history.selectors.asset'),
        multiple: false,
        paramKey: AccountHistoryQueryKeys.ASSET,
        to: 'both',
        // A value type of asset opens the search editor, which ignores `suggest`.
        ...(assets ? { suggest: assets } : { searchAsset, valueType: FilterValueTypes.ASSET }),
      }),
      SharedFieldKinds.ASSET,
      resolvers,
    ),
    ...location,
  ];
}

/** The page's account, asset and location as the bar's params bag. */
export function accountHistoryParams(
  account: Ref<string | undefined>,
  asset: Ref<string | undefined>,
  location: Ref<string | undefined>,
): WritableComputedRef<PillParams> {
  return toPillParams({
    [AccountHistoryQueryKeys.ACCOUNT]: optionalStringParam(account),
    [AccountHistoryQueryKeys.ASSET]: optionalStringParam(asset),
    [AccountHistoryQueryKeys.LOCATION]: optionalStringParam(location),
  });
}
