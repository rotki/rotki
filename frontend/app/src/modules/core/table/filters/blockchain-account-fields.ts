import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef, ValueSwatch } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * The chain pill: which chains of the shown category an account has to be on. Param-bound like the
 * account and tag pills, so this table declares no matchers at all — every filter it has reaches
 * the request the same way.
 *
 * The values are the category's own chain ids (evm has around fifteen, bitcoin two, solana one),
 * and a group that survives is narrowed to the chains that matched, which is what makes its value
 * add up to the chains being shown rather than all of them.
 */
export function toAccountChainField(
  t: Translate,
  resolvers: SharedFieldResolvers,
  chains: () => string[],
): FieldDef {
  return decorateSharedField(
    toParamFieldDef({
      key: 'chain',
      label: t('account_balances.filter_field_labels.chain'),
      multiple: true,
      paramKey: 'chain',
      suggest: chains,
      to: 'both',
    }),
    SharedFieldKinds.CHAIN,
    resolvers,
  );
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
