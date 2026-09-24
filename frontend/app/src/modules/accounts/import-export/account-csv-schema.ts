import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import { Blockchain } from '@rotki/common';
import { z } from 'zod';
import { type AccountTarget, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { getKeyType, guessPrefix, isPrefixed } from '@/modules/accounts/xpub';

const CSVRow = z.object({
  address: z.string(),
  addressExtras: z.string().transform(value => serializedStringToRecord(value)),
  chain: z.string(),
  label: z.string().optional(),
  tags: z.string().optional().transform(value => value ? value.split(';') : []),
});

export const CSVSchema = z.array(CSVRow);

export type CSVRow = z.infer<typeof CSVRow>;

function serializedStringToRecord(serialized: string): Record<string, string> {
  const record: Record<string, string> = {};
  serialized.split('&').forEach((pair) => {
    const [key, value] = pair.split('=');
    if (key) {
      record[key] = value || '';
    }
  });

  return record;
}

export function serializeRecordToString(record: Record<string, string>): string {
  return Object.entries(record)
    .map(([key, value]) => `${key}=${value}`)
    .join('&');
}

function csvToAccount(acc: CSVRow): AccountPayload {
  return {
    address: acc.address,
    label: acc.label,
    tags: acc.tags || null,
  };
}

/**
 * One row of an import as the batch runs it: an account to add, or one that is already tracked and
 * is only reported.
 */
export type ImportItem =
  | { readonly type: 'add'; readonly chain: string; readonly account: AddAccountsPayload | XpubAccountPayload }
  | { readonly type: 'tracked'; readonly chain: string; readonly target: AccountTarget };

/** The CSV's word for "every EVM chain", which an addition is tracked under as the pseudo-chain. */
function importChain(row: CSVRow): string {
  return row.chain === 'evm' ? EVM_PSEUDO_CHAIN : row.chain;
}

function isXpubRow(row: CSVRow): boolean {
  return row.chain !== Blockchain.ETH2 && isPrefixed(row.address) !== null;
}

/** A row the user is not tracking yet, as the payload its addition sends. */
export function additionItem(row: CSVRow): ImportItem {
  const account: AddAccountsPayload | XpubAccountPayload = isXpubRow(row)
    ? {
        label: row.label,
        tags: row.tags,
        xpub: {
          derivationPath: row.addressExtras.derivationPath,
          xpub: row.address,
          xpubType: getKeyType(guessPrefix(row.address)),
        },
      }
    : { payload: [csvToAccount(row)] };
  return { account, chain: importChain(row), type: 'add' };
}

/** A row naming an account that is already tracked, identified the way its addition would be. */
export function trackedItem(row: CSVRow): ImportItem {
  const target: AccountTarget = isXpubRow(row)
    ? { derivationPath: row.addressExtras.derivationPath, kind: 'xpub', xpub: row.address }
    : { address: row.address, kind: 'address' };
  return { chain: importChain(row), target, type: 'tracked' };
}

export function createValidatorAction(mode: 'add' | 'edit', data: Eth2Validator): StakingValidatorManage {
  return {
    chain: Blockchain.ETH2,
    data,
    mode,
    type: 'validator',
  };
}

export function doesAccountExist(row: CSVRow, accounts: { address: string; chain: string }[]): boolean {
  return accounts.some(account => account.chain === row.chain && account.address === row.address);
}

export function getChainType(chains: string[], isEvmCompatible: (chain: string) => boolean): string {
  const EVM_CHAIN_TYPE = 'evm';

  if (chains.length > 1 && chains.some(isEvmCompatible)) {
    return EVM_CHAIN_TYPE;
  }

  return chains[0];
}
