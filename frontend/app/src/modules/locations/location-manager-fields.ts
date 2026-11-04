import type { Ref, WritableComputedRef } from 'vue';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { type PillParams, stringParam, toPillParams } from '@/modules/core/table/param-refs';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * The pill-bar field of the location tree: a name to look for.
 *
 * @remarks
 * Param-bound, because the page holds the whole tree and narrows it in memory, keeping the
 * ancestors of each match.
 */
export function toLocationTreeFields(t: Translate): FieldDef[] {
  return [
    toParamFieldDef({
      freeText: true,
      key: 'name',
      label: (): string => t('common.name'),
      multiple: false,
      paramKey: 'name',
      to: 'both',
    }),
  ];
}

export function locationTreeParams(name: Ref<string>): WritableComputedRef<PillParams> {
  return toPillParams({ name: stringParam(name) });
}

/** What the alias fields need from the Vue layer to be built. */
export interface LocationAliasFieldOptions {
  /** The locations the saved aliases point at, offered for the location pill. */
  readonly locations: () => string[];
}

/**
 * The pill-bar fields of the location aliases: an alias to look for, and the location aliases
 * point at.
 *
 * @remarks
 * Param-bound, because the aliases are few and held in memory.
 */
export function toLocationAliasFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: LocationAliasFieldOptions,
): FieldDef[] {
  return [
    toParamFieldDef({
      freeText: true,
      key: 'alias',
      label: (): string => t('location_manager.aliases.alias'),
      multiple: false,
      paramKey: 'alias',
      to: 'both',
    }),
    decorateSharedField(
      toParamFieldDef({
        key: 'location',
        label: (): string => t('common.location'),
        multiple: false,
        paramKey: 'location',
        suggest: options.locations,
        to: 'both',
      }),
      SharedFieldKinds.LOCATION,
      resolvers,
    ),
  ];
}

export function locationAliasParams(alias: Ref<string>, location: Ref<string>): WritableComputedRef<PillParams> {
  return toPillParams({ alias: stringParam(alias), location: stringParam(location) });
}
