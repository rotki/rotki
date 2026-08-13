import type { Eth2ValidatorEntry } from '@rotki/common';
import type { RepullingEthStakingPayload } from '@/modules/history/events/event-payloads';
import { z, type ZodType } from 'zod';
import { Exchange } from '@/modules/balances/types/exchanges';
import { requiredField } from '@/modules/core/form/fields';

/**
 * The three repulling forms are not one schema with a flag. They share the optional time range and
 * nothing else: the blockchain one edits a chain and an address, the exchange one an exchange that
 * never reaches the payload, and eth staking an entry type. Only the range is factored out.
 *
 * The range is required whenever its picker is on screen, and the epoch is a date like any other:
 * `required` reported on a cleared picker, which arrives as undefined, never on 0.
 */
function timeRange(required: boolean, message: string): {
  fromTimestamp: ZodType<number | undefined>;
  toTimestamp: ZodType<number | undefined>;
} {
  const field = required ? z.number({ error: message }) : z.number().optional();
  return { fromTimestamp: field, toTimestamp: field };
}

export interface RepullingBlockchainFormState {
  address?: string;
  chain?: string;
  fromTimestamp?: number;
  toTimestamp?: number;
}

export interface RepullingExchangeFormState {
  /** Local to the form: the request carries the exchange itself, not through the shared payload. */
  exchange?: Exchange;
  fromTimestamp?: number;
  toTimestamp?: number;
}

export type RepullingFilterMode = 'addresses' | 'validator_indices';

export interface RepullingEthStakingFormState {
  entryType: string;
  /** Which of the two selections below is sent. Never part of the request itself. */
  filterMode: RepullingFilterMode;
  fromTimestamp?: number;
  toTimestamp?: number;
  selectedAddresses: string[];
  selectedValidators: Eth2ValidatorEntry[];
}

export function repullingBlockchainSchema(rangeRequired: string): ZodType {
  return z.object({
    /*
     * Neither carries a rule. The address is here so an error the api reports against it has
     * somewhere to land, which vuelidate needed a no-op validator to do at all.
     */
    address: z.string().optional(),
    chain: z.string().optional(),
    ...timeRange(true, rangeRequired),
  });
}

export function repullingExchangeSchema(messages: { exchangeRequired: string; rangeRequired: string }, hasDateRange: boolean): ZodType {
  return z.object({
    exchange: Exchange.or(z.undefined()).refine(value => value !== undefined, { error: messages.exchangeRequired }),
    ...timeRange(hasDateRange, messages.rangeRequired),
  });
}

/** The request the eth staking form's state projects to: one selection or the other, never both. */
export function toEthStakingPayload(state: RepullingEthStakingFormState): RepullingEthStakingPayload {
  const base: RepullingEthStakingPayload = {
    entryType: state.entryType,
    fromTimestamp: state.fromTimestamp,
    toTimestamp: state.toTimestamp,
  };

  return state.filterMode === 'validator_indices'
    ? { ...base, validatorIndices: state.selectedValidators.map(validator => validator.index) }
    : { ...base, addresses: state.selectedAddresses };
}

/**
 * The two selections carry no rule: either may be empty, which the request reads as "all of them".
 * They are still in the state, because changing one is an edit the dialog has to prompt about.
 */
export function repullingEthStakingSchema(messages: { entryTypeRequired: string; rangeRequired: string }, hasDateRange: boolean): ZodType {
  return z.object({
    entryType: requiredField(messages.entryTypeRequired),
    filterMode: z.string(),
    selectedAddresses: z.array(z.string()),
    selectedValidators: z.array(z.custom<Eth2ValidatorEntry>()),
    ...timeRange(hasDateRange, messages.rangeRequired),
  });
}
