import { ALL_EVM_CHAINS } from '@/modules/accounts/accounts.activity';
import { type AddressCheck, addressCheckFor } from '@/modules/accounts/blockchain/address-check';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAddressCheckReturn {
  addressCheck: (chain: string) => AddressCheck | undefined;
}

/**
 * Picks the {@link AddressCheck} for the chain an account is added to, every EVM chain at once
 * included. A chain the supported list does not know yet gets no hex check, so its entries are left
 * to the backend.
 */
export function useAddressCheck(): UseAddressCheckReturn {
  const { isEvmCompatible } = useSupportedChains();

  const addressCheck = (chain: string): AddressCheck | undefined =>
    addressCheckFor(chain, chain === ALL_EVM_CHAINS || isEvmCompatible(chain));

  return { addressCheck };
}
