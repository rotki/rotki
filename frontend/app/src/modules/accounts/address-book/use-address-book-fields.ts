import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Matcher } from '@/modules/core/table/filters/use-address-book-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { Blockchain } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import {
  toAddressBookChainField,
  toAddressBookFields,
  toAddressBookStrictField,
} from '@/modules/core/table/filters/address-book-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/**
 * The pill-bar fields for the address book table: its two matchers, plus the chain and the
 * strict-chain toggle that used to sit in controls of their own beside the bar.
 *
 * Built inside a computed so the labels track the locale: fields built once at setup keep the
 * language they were created in until the component remounts.
 */
export function useAddressBookFields(matchers: MaybeRefOrGetter<Matcher[]>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Address and chain-name resolution is the same for every table filtering on them, so it comes
  // from one place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const { supportedChains } = useSupportedChains();

  // The same list the chain selector offered here: every supported chain minus eth staking. The
  // selector took that exclusion from this page's own `exclude-eth-staking`, which held whether or
  // not the eth2 module was on, so the module flag never entered into it.
  const chainIds = computed<string[]>(() => get(supportedChains)
    .map(({ id }) => id)
    .filter(id => id !== Blockchain.ETH2));

  return computed<FieldDef[]>(() => [
    ...toAddressBookFields(toValue(matchers), shared, t),
    toAddressBookChainField(t, shared, (): string[] => get(chainIds)),
    toAddressBookStrictField(t),
  ]);
}
