import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { decorateSharedField, type SharedFieldKind, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { AddressBookFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-address-book-filter';
import { toFieldDef, toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * Short, noun-style pill labels. The matcher `description` is a long "filter by …" hint that reads
 * badly on a pill, so each field gets a concise label keyed by its wire key.
 */
function shortLabels(t: Translate): Record<string, string> {
  return {
    [AddressBookFilterValueKeys.ADDRESS]: t('address_book.filter_field_labels.address'),
    [AddressBookFilterValueKeys.NAME]: t('address_book.filter_field_labels.name'),
  };
}

// An address is typed rather than picked — the address book is a list of arbitrary addresses, not
// of tracked ones — and is shortened and scrambled for display, as everywhere else.
const sharedKinds: Partial<Record<string, SharedFieldKind>> = {
  [AddressBookFilterValueKeys.ADDRESS]: SharedFieldKinds.ADDRESS,
};

/**
 * The chain an entry is for, as a param-bound pill. It rides the `blockchain` param rather than a
 * matcher, which is what lets the bar absorb the chain selector that used to sit beside it.
 *
 * Single-valued: the backend takes one chain, and the entry either names that chain or names none.
 */
export function toAddressBookChainField(
  t: Translate,
  resolvers: SharedFieldResolvers,
  chains: () => string[],
): FieldDef {
  return decorateSharedField(
    toParamFieldDef({
      key: 'blockchain',
      label: t('address_book.filter_field_labels.chain'),
      multiple: false,
      paramKey: 'blockchain',
      suggest: chains,
      to: 'both',
    }),
    SharedFieldKinds.CHAIN,
    resolvers,
  );
}

/**
 * The strict-chain toggle as a param-bound boolean pill. A boolean field has no editor and no value
 * segment: adding the pill turns it on, removing it turns it off, which is the whole of its state.
 *
 * It only means anything alongside a chain, since it narrows that chain's entries to the ones
 * written for it rather than for every chain — hence the hint, which is the checkbox's old one.
 */
export function toAddressBookStrictField(t: Translate): FieldDef {
  return toParamFieldDef({
    hint: t('address_book.strict_blockchain_filter.hint'),
    key: 'strictBlockchain',
    label: t('address_book.strict_blockchain_filter.label'),
    multiple: false,
    paramKey: 'strictBlockchain',
    to: 'both',
    valueType: FilterValueTypes.BOOLEAN,
  });
}

/** The pill-bar fields for the address book table: its two matchers, drawn as pills. */
export function toAddressBookFields(
  matchers: Matcher[],
  resolvers: SharedFieldResolvers,
  t: Translate,
): FieldDef[] {
  const labels = shortLabels(t);

  return matchers.map((matcher) => {
    const field = decorateSharedField(toFieldDef(matcher), sharedKinds[String(matcher.keyValue)], resolvers);
    return {
      ...field,
      ...(labels[field.key] ? { label: labels[field.key] } : {}),
      // The name is a substring search over names the user wrote, so there is no list to offer.
      ...(field.key === AddressBookFilterValueKeys.NAME ? { freeText: true } : {}),
    };
  });
}
