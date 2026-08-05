import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Matcher } from '@/modules/core/table/filters/use-assets-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { IgnoredAssetHandlingType } from '@/modules/assets/types';
import {
  toAssetIgnoredField,
  toAssetOwnedField,
  toAssetWhitelistedField,
  toManagedAssetFields,
} from '@/modules/core/table/filters/managed-asset-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/**
 * Assembles the pill-bar fields for the managed assets table: the matcher-backed ones plus the
 * three filters that used to live in the status dropdown beside the bar — owned only, whitelisted
 * only, and how ignored assets are handled — each now a param-bound pill, so every filter this
 * table has is in one place.
 */
export function useManagedAssetFields(
  matchers: MaybeRefOrGetter<Matcher[]>,
  ignoredCount: MaybeRefOrGetter<number>,
): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Chain and asset-type resolution is the same for every table filtering on them, so it comes
  // from one place rather than being restated here.
  const shared = useSharedFieldResolvers();

  // How many assets are ignored is part of what the value says, the way it was part of the radio
  // label it replaces: picking "only ignored" is a different decision when the count is zero.
  const resolveIgnoredLabel = (value: string): string => value === IgnoredAssetHandlingType.SHOW_ONLY
    ? t('assets.filter_field_labels.ignored_only', { count: toValue(ignoredCount) })
    : t('assets.filter_field_labels.ignored_all');

  // Built inside the computed so every label tracks the locale: a field built once at setup keeps
  // the language it was created in until the component remounts.
  return computed<FieldDef[]>(() => [
    ...toManagedAssetFields(toValue(matchers), shared, t),
    toAssetOwnedField(t),
    toAssetWhitelistedField(t),
    toAssetIgnoredField(t, resolveIgnoredLabel),
  ]);
}
