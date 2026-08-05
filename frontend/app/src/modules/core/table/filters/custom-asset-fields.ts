import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { CustomAssetFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-custom-assets-filter';
import { toFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * Short, noun-style pill labels. The matcher `description` is a long "filter by …" hint that reads
 * badly on a pill, so each field gets a concise label keyed by its wire key.
 */
function shortLabels(t: Translate): Record<string, string> {
  return {
    [CustomAssetFilterValueKeys.CUSTOM_ASSET_TYPE]: t('assets.filter_field_labels.type'),
    [CustomAssetFilterValueKeys.NAME]: t('assets.filter_field_labels.name'),
  };
}

/**
 * The name is written rather than picked: the matcher offers no suggestions for it, because there
 * is no list of every custom asset name to offer. The type is picked — its suggestions are the
 * types the user has actually created.
 */
const freeTextKeys = new Set<string>([CustomAssetFilterValueKeys.NAME]);

/** The pill-bar fields for the custom assets table: the same two matchers, drawn as pills. */
export function toCustomAssetFields(matchers: Matcher[], t: Translate): FieldDef[] {
  const labels = shortLabels(t);
  return matchers.map((matcher) => {
    const field = toFieldDef(matcher);
    return {
      ...field,
      ...(labels[field.key] ? { label: labels[field.key] } : {}),
      ...(freeTextKeys.has(field.key) ? { freeText: true } : {}),
    };
  });
}
