import type { SearchMatcher } from '@/modules/core/table/filtering';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef, ValueSwatch } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toFieldDef, toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/** The blockchain account table's own wire keys. */
const CHAIN_KEY = 'chain';

/**
 * The matcher-backed pill-bar fields for the blockchain accounts table, which today is the chain
 * matcher alone: its long "filter by …" description becomes a short pill label and its values are
 * drawn with their chain logo. The account and tag pills are param-bound and built separately.
 */
export function toBlockchainAccountFields(
  matchers: SearchMatcher<string, string>[],
  resolvers: SharedFieldResolvers & { readonly t: Translate },
): FieldDef[] {
  const { t } = resolvers;

  return matchers.map((field) => {
    const mapped = toFieldDef(field);
    if (mapped.key !== CHAIN_KEY)
      return mapped;

    return {
      ...decorateSharedField(mapped, SharedFieldKinds.CHAIN, resolvers),
      label: t('account_balances.filter_field_labels.chain'),
    };
  });
}

/** One selectable tag: its name is the wire value, its colours are how it is recognised. */
export interface TagFieldOption {
  readonly name: string;
  readonly swatch: ValueSwatch;
}

/**
 * The account tags as a param-bound pill field. Tags are an external filter rather than a matcher
 * — they ride the `tags` param, which goes to both the request and the URL — so modelling them as
 * a field is what folds the standalone tag selector into the one bar.
 *
 * A tag carries the two colours the user picked for it, and that pairing is how a tag is
 * recognised everywhere else in the app, so the value keeps them here too (`resolveSwatch`)
 * instead of falling back to plain text.
 */
export function toAccountTagsField(t: Translate, tags: () => TagFieldOption[]): FieldDef {
  // Computed rather than rebuilt per call: `resolveSwatch` is called once per candidate value on
  // every keystroke while the bar narrows, and a rebuild there is a full pass over every tag.
  const byName = computed<Map<string, TagFieldOption>>(
    () => new Map(tags().map(tag => [tag.name, tag])),
  );
  const names = computed<string[]>(() => tags().map(tag => tag.name));

  return toParamFieldDef({
    key: 'tags',
    label: t('account_balances.filter_field_labels.tags'),
    multiple: true,
    paramKey: 'tags',
    resolveSwatch: (value: string): ValueSwatch | undefined => get(byName).get(value)?.swatch,
    suggest: (): string[] => get(names),
    to: 'both',
  });
}
