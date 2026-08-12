import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { AddressBookFilterKeys } from '@/modules/accounts/address-book/use-address-book-filter';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef, toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

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
      label: (): string => t('address_book.filter_field_labels.chain'),
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
    hint: (): string => t('address_book.strict_blockchain_filter.hint'),
    key: 'strictBlockchain',
    label: (): string => t('address_book.strict_blockchain_filter.label'),
    multiple: false,
    paramKey: 'strictBlockchain',
    to: 'both',
    valueType: FilterValueTypes.BOOLEAN,
  });
}

/** The pill-bar fields for the address book table: a name and an address, both typed. */
export function toAddressBookFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
): FieldDef[] {
  return [
    // A substring search over names the user wrote, which is what the backend does with it
    // (`name_substring`).
    toNameField(AddressBookFilterKeys.NAME, (): string => t('address_book.filter_field_labels.name')),
    // The address kind carries the shortening, the scrambling and the validation, so an incomplete
    // address is neither offered nor applied.
    decorateSharedField(
      toMatchFieldDef({
        key: AddressBookFilterKeys.ADDRESS,
        label: (): string => t('address_book.filter_field_labels.address'),
        multiple: true,
      }),
      SharedFieldKinds.ADDRESS,
      resolvers,
    ),
  ];
}
