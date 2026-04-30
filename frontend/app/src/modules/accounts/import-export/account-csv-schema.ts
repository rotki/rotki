import type { AccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import { Blockchain } from '@rotki/common';
import { z } from 'zod/v4';

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

export function csvToAccount(acc: CSVRow): AccountPayload {
  return {
    address: acc.address,
    label: acc.label,
    tags: acc.tags || null,
  };
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
