import type { AssetBalances } from '@/modules/balances/types/balances';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import { AssetBalance, type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';
import { type Collection, CollectionCommonFields } from '@/modules/core/common/collection';

export const KrakenAccountType = z.enum(['starter', 'intermediate', 'pro']);

export type KrakenAccountType = z.infer<typeof KrakenAccountType>;

const GATE_LOCATIONS = ['global', 'europe', 'us'] as const;
const OKX_LOCATIONS = ['global', 'eea', 'us'] as const;

/**
 * Sets rather than the tuples themselves: `includes` on a readonly tuple narrows its argument to the
 * member union, which an `unknown` narrowed only to `string` cannot satisfy, while a set lookup
 * takes a plain string.
 */
const GATE_LOCATION_VALUES: ReadonlySet<string> = new Set(GATE_LOCATIONS);
const OKX_LOCATION_VALUES: ReadonlySet<string> = new Set(OKX_LOCATIONS);

export const GateLocation = z.enum(GATE_LOCATIONS);

export const OkxLocation = z.enum(OKX_LOCATIONS);

export type GateLocation = z.infer<typeof GateLocation>;

export type OkxLocation = z.infer<typeof OkxLocation>;

function isValidGateLocation(val: unknown): val is GateLocation {
  return typeof val === 'string' && GATE_LOCATION_VALUES.has(val);
}

function isValidOkxLocation(val: unknown): val is OkxLocation {
  return typeof val === 'string' && OKX_LOCATION_VALUES.has(val);
}

/** Which exchange connection to pull the history of. */
export const QueryExchangeEventsPayload = z.object({
  identifier: z.string(),
});

export type QueryExchangeEventsPayload = z.infer<typeof QueryExchangeEventsPayload>;

/** An exchange connector and what setting up an API key for it needs. */
export const ExchangeConnector = z.object({
  connector: z.string(),
  location: z.string(),
  isExchangeWithPassphrase: z.boolean(),
  isExchangeWithoutApiSecret: z.boolean(),
  experimental: z.boolean(),
});

export type ExchangeConnector = z.infer<typeof ExchangeConnector>;

export const ExchangeConnectors = z.array(ExchangeConnector);

export const Exchange = z.object({
  /** The stable identifier of the connection, which survives renames. */
  identifier: z.string(),
  name: z.string(),
  connector: z.string(),
  /** The exchange location the connection's data belongs to. */
  location: z.string(),
  krakenAccountType: KrakenAccountType.optional(),
  gateLocation: z.preprocess(
    (val) => {
      if (val === undefined)
        return undefined;
      if (isValidGateLocation(val))
        return val;
      return 'global';
    },
    GateLocation.optional(),
  ),
  okxLocation: z.preprocess(
    (val) => {
      if (val === undefined)
        return undefined;
      if (isValidOkxLocation(val))
        return val;
      return 'global';
    },
    OkxLocation.optional(),
  ),
});

export type Exchange = z.infer<typeof Exchange>;

export const Exchanges = z.array(Exchange);

export type Exchanges = z.infer<typeof Exchanges>;

export interface ExchangeInfo {
  readonly location: string;
  readonly balances: AssetBalances;
  readonly total: BigNumber;
}

export type ExchangeData = Record<string, AssetBalances>;

export interface EditExchange {
  readonly exchange: Exchange;
  readonly newName?: string;
}

interface ExchangePayload {
  /** Set when editing an existing connection. */
  readonly identifier?: string;
  readonly name: string;
  /** The exchange connector; for exchanges it is spelled like the exchange's location. */
  readonly location: string;
  readonly apiKey: string;
  readonly apiSecret: string;
  readonly passphrase: string;
  readonly krakenAccountType?: KrakenAccountType;
  readonly krakenFuturesApiKey?: string;
  readonly krakenFuturesApiSecret?: string;
  readonly binanceMarkets?: string[];
  readonly binanceHistoryStartTs?: number;
  readonly gateLocation?: GateLocation;
  readonly okxLocation?: OkxLocation;
}

export interface ExchangeFormData extends ExchangePayload {
  readonly mode: 'edit' | 'add';
  readonly newName?: string;
}

const ExchangeSavingsEvent = z.object({
  amount: NumericString,
  asset: z.string().min(1),
  location: z.string(),
  timestamp: z.number(),
});

export type ExchangeSavingsEvent = z.infer<typeof ExchangeSavingsEvent>;

export const ExchangeSavingsCollectionResponse = CollectionCommonFields.extend({
  assets: z.array(z.string()),
  entries: z.array(ExchangeSavingsEvent),
  received: z.array(AssetBalance),
  totalValue: NumericString,
});

export type ExchangeSavingsCollectionResponse = z.infer<typeof ExchangeSavingsCollectionResponse>;

export interface ExchangeSavingsCollection extends Collection<ExchangeSavingsEvent> {
  assets: string[];
  received: AssetBalance[];
}

export interface ExchangeSavingsRequestPayload extends PaginationRequestPayload<ExchangeSavingsEvent> {
  readonly location: string;
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
}
