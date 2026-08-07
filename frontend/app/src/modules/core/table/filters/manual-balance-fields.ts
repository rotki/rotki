import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, type SharedFieldKind, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { type TagFieldOption, toTagsField } from '@/modules/core/table/filters/shared/tag-field';
import { ManualBalanceFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-manual-balances-filter';
import { toFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * Short, noun-style pill labels. The matcher `description` is already short here, but keying the
 * labels off the wire key keeps this table reading like the others.
 */
function shortLabels(t: Translate): Record<string, string> {
  return {
    [ManualBalanceFilterValueKeys.ASSET]: t('common.asset'),
    [ManualBalanceFilterValueKeys.LABEL]: t('common.label'),
    [ManualBalanceFilterValueKeys.LOCATION]: t('common.location'),
  };
}

// Asset and location are shared kinds, so both look the same here as they do in the history bar.
const sharedKinds: Partial<Record<string, SharedFieldKind>> = {
  [ManualBalanceFilterValueKeys.ASSET]: SharedFieldKinds.ASSET,
  [ManualBalanceFilterValueKeys.LOCATION]: SharedFieldKinds.LOCATION,
};

// A label is the name the user gave the balance, so there is no list of them to offer: it is typed.
const freeTextKeys = new Set<string>([ManualBalanceFilterValueKeys.LABEL]);

/**
 * The pill-bar fields for the manual balances table: its three matchers, plus the tags that used to
 * sit in a selector of their own beside the bar. Tags are param-bound (`tags`, to request and url),
 * which is what lets the bar absorb them.
 */
export function toManualBalanceFields(
  matchers: Matcher[],
  resolvers: SharedFieldResolvers,
  t: Translate,
  tags: () => TagFieldOption[],
): FieldDef[] {
  const labels = shortLabels(t);

  const matcherFields = matchers.map((matcher) => {
    const field = decorateSharedField(toFieldDef(matcher), sharedKinds[String(matcher.keyValue)], resolvers);
    return {
      ...field,
      ...(labels[field.key] ? { label: labels[field.key] } : {}),
      ...(freeTextKeys.has(field.key) ? { freeText: true } : {}),
    };
  });

  return [...matcherFields, toTagsField(t, tags)];
}
