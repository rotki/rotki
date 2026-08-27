import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { Blockchain } from '@rotki/common';
import {
  toAddressBookChainField,
  toAddressBookFields,
  toAddressBookStrictField,
} from '@/modules/accounts/address-book/address-book-fields';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/**
 * The pill-bar fields for the address book table: its name and address, plus the chain and the
 * strict-chain toggle.
 */
export function useAddressBookFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const { supportedChains } = useSupportedChains();

  const chainIds = computed<string[]>(() => get(supportedChains)
    .map(({ id }) => id)
    .filter(id => id !== Blockchain.ETH2));

  return [
    ...toAddressBookFields(shared, t),
    toAddressBookChainField(t, shared, (): string[] => get(chainIds)),
    toAddressBookStrictField(t),
  ];
}
