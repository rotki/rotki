import type { FieldText } from '@/modules/core/table/pill/core/text';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';

/** What an account field needs from its table's account list, grouped so the argument list stays short. */
export interface AccountFieldOptions {
  /** The addresses offered as the field's values. */
  readonly suggest: () => string[];
  /** Address -> the name shown on the pill, else the shortened address. */
  readonly resolveLabel: (value: string) => string;
  /** Address -> the muted address shown beside a name. */
  readonly resolveCaption: (value: string) => string | undefined;
  /** Address -> `address name tags`, so the bar can find an account by any of them. */
  readonly resolveKeywords: (value: string) => string | undefined;
  /** Address -> whether its name is still resolving, so the row is a skeleton rather than a flash of address. */
  readonly resolveLoading?: (value: string) => boolean;
}

/** Where an account field's picked addresses are transported, which differs per table. */
export interface AccountFieldBinding {
  readonly label: FieldText;
  readonly paramKey: string;
  readonly to: 'request' | 'url' | 'both';
}

/**
 * The account pill, shared by every table that filters on tracked accounts.
 *
 * Always param-bound and multi-valued: an address is picked, not typed, and a table that offers
 * accounts at all offers all of them. It carries its addresses as values so an account can be
 * applied straight from the bar's inline input the way a location or protocol can — matched on its
 * address, name or ENS, none of which the pill's own label reliably shows (it is a name, or a
 * shortened and scrambled address).
 *
 * Which addresses exist, and what each is called, is the table's own business: history offers the
 * accounts its events mention, the balances table the accounts of the category being shown. Only
 * how they read is shared, which is the point — the two pills looked alike and were not.
 */
export function toAccountField(binding: AccountFieldBinding, accounts: AccountFieldOptions): FieldDef {
  return toParamFieldDef({
    // The accounts table's old matcher stored `label (address)`, or a bare address when the
    // account had no name. Only the address survives into the field's own form.
    fromLegacy: (value: string): string => value.match(/^.+?\s*\(([^)]+)\)$/)?.[1] ?? value,
    display: DisplayKinds.ACCOUNT,
    key: 'account',
    label: binding.label,
    multiple: true,
    paramKey: binding.paramKey,
    resolveCaption: accounts.resolveCaption,
    resolveKeywords: accounts.resolveKeywords,
    resolveLabel: accounts.resolveLabel,
    resolveLoading: accounts.resolveLoading,
    suggest: accounts.suggest,
    to: binding.to,
  });
}
