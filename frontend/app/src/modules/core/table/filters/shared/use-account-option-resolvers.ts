import type { MaybeRefOrGetter } from 'vue';
import type { AccountFieldOptions } from '@/modules/core/table/filters/shared/account-field';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useScramble } from '@/modules/settings/use-scramble';

/** One tracked account, as the account pill needs to read it. */
export interface AccountOption {
  readonly address: string;
  /** Its tracked/ENS name, absent when it has none. */
  readonly name?: string;
  readonly tags: string[];
}

/**
 * How an account pill reads a table's accounts: a name with the shortened address beside it, or
 * the shortened address alone, and the full address, name and tags as search keywords.
 *
 * @remarks
 * The shortened address is scrambled when privacy mode asks for it. The keywords keep the full,
 * unscrambled address, since that is what a user pastes.
 *
 * @param byAddress - the table's accounts, keyed by address, in the order they are offered
 */
export function useAccountOptionResolvers(byAddress: MaybeRefOrGetter<Map<string, AccountOption>>): AccountFieldOptions {
  const { scrambleAddress } = useScramble();

  function shortAddress(address: string): string {
    return truncateAddress(scrambleAddress(address), 4);
  }

  return {
    resolveCaption: (address: string): string | undefined =>
      toValue(byAddress).get(address)?.name ? shortAddress(address) : undefined,
    resolveKeywords: (address: string): string | undefined => {
      const option = toValue(byAddress).get(address);
      return option && `${option.address} ${option.name ?? ''} ${option.tags.join(' ')}`.toLowerCase();
    },
    resolveLabel: (address: string): string => toValue(byAddress).get(address)?.name ?? shortAddress(address),
    suggest: (): string[] => [...toValue(byAddress).keys()],
  };
}
