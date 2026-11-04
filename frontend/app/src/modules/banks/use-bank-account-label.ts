import type { BankAccountBalance } from '@/modules/banks/types';
import { useScramble } from '@/modules/settings/use-scramble';

/** How an account reads in a list: its name, with its IBAN under it when the name is not the IBAN. */
export interface BankAccountLabel {
  readonly title: string;
  readonly subtitle?: string;
}

interface UseBankAccountLabelReturn {
  accountLabel: (account: Pick<BankAccountBalance, 'iban' | 'name'>) => BankAccountLabel;
}

const IBAN_GROUP = /.{1,4}/g;

function compact(value: string): string {
  return value.replaceAll(/\s/g, '').toUpperCase();
}

/**
 * Labels bank accounts for display, hiding their IBANs in privacy mode.
 *
 * @remarks
 * Some banks name an account by its IBAN or account number, so the name is scrambled whenever it
 * is one of those. An IBAN keeps its country code so the scrambled value still reads as one, and
 * is printed in the usual groups of four.
 */
export function useBankAccountLabel(): UseBankAccountLabelReturn {
  const { scrambleAddress, scrambleIdentifier } = useScramble();

  function displayIban(iban: string): string {
    const value = compact(iban);
    const shown = value.slice(0, 2) + scrambleAddress(value.slice(2)).toUpperCase();
    return shown.match(IBAN_GROUP)?.join(' ') ?? shown;
  }

  function displayName(name: string, iban: string | null): string {
    if (iban !== null && compact(name) === compact(iban))
      return displayIban(iban);
    if (/^\d+$/.test(name))
      return scrambleIdentifier(name, 10 ** (name.length - 1), 10 ** name.length - 1);
    return name;
  }

  function accountLabel({ iban, name }: Pick<BankAccountBalance, 'iban' | 'name'>): BankAccountLabel {
    const title = displayName(name, iban);
    if (iban === null || compact(name) === compact(iban))
      return { title };
    return { subtitle: displayIban(iban), title };
  }

  return { accountLabel };
}
