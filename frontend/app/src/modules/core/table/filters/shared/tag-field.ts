import type { FieldDef, ValueSwatch } from '@/modules/core/table/pill/core/types';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/** One selectable tag: its name is the wire value, its colours are how it is recognised. */
export interface TagFieldOption {
  readonly name: string;
  readonly swatch: ValueSwatch;
}

/**
 * The tags pill, shared by every table that filters on them.
 *
 * Tags are an external filter rather than a matcher — they ride the `tags` param, which goes to
 * both the request and the URL — so modelling them as a field is what folds a standalone tag
 * selector into the one bar.
 *
 * A tag carries the two colours the user picked for it, and that pairing is how a tag is
 * recognised everywhere else in the app, so the value keeps them here too (`resolveSwatch`)
 * instead of falling back to plain text.
 */
export function toTagsField(t: Translate, tags: () => TagFieldOption[]): FieldDef {
  // Computed rather than rebuilt per call: `resolveSwatch` is called once per candidate value on
  // every keystroke while the bar narrows, and a rebuild there is a full pass over every tag.
  const byName = computed<Map<string, TagFieldOption>>(
    () => new Map(tags().map(tag => [tag.name, tag])),
  );
  const names = computed<string[]>(() => tags().map(tag => tag.name));

  return toParamFieldDef({
    key: 'tags',
    label: t('common.tags'),
    multiple: true,
    paramKey: 'tags',
    resolveSwatch: (value: string): ValueSwatch | undefined => get(byName).get(value)?.swatch,
    suggest: (): string[] => get(names),
    to: 'both',
  });
}
