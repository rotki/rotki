import { z, type ZodType } from 'zod';
import { type MessageKey, msg } from '@/message-key';
import { GateLocation, KrakenAccountType, OkxLocation } from '@/modules/balances/types/exchanges';

/**
 * Which fields the exchange key form demands, and which parts of it render, is decided entirely by
 * the chosen exchange and whether the form is adding or editing. Keeping those decisions here means
 * they are answerable without mounting anything, and that the rules and the template read from one
 * description rather than from a dozen inline `computed`s.
 *
 * @packageDocumentation
 */

/** Exchanges that need more than the usual key and secret, or that render an extra section. */
const BINANCE_EXCHANGES = ['binance', 'binanceus'];

/** Exchanges whose keys take a while to become usable, so the form warns before saving. */
const SLOW_KEY_EXCHANGES = ['kraken', 'coinbase', 'coinbaseprime'];

/** Exchanges whose API only serves a limited history window. */
const HISTORY_LIMIT_MESSAGES: Record<string, MessageKey> = {
  bybit: msg.$t('exchange_keys_form.history_limit_warning.bybit'),
  cryptocom: msg.$t('exchange_keys_form.history_limit_warning.cryptocom'),
  htx: msg.$t('exchange_keys_form.history_limit_warning.htx'),
};

/** What the backend says a given exchange supports. Empty lists mean "not loaded yet". */
export interface ExchangeCapabilities {
  readonly withoutApiSecret: string[];
  readonly withPassphrase: string[];
}

export function isEditing(mode: string): boolean {
  return mode === 'edit';
}

export function isBinance(location: string): boolean {
  return BINANCE_EXCHANGES.includes(location);
}

export function isGate(location: string): boolean {
  return location === 'gate';
}

export function isKraken(location: string): boolean {
  return location === 'kraken';
}

export function isOkx(location: string): boolean {
  return location === 'okx';
}

export function isCoinbase(location: string): boolean {
  return location === 'coinbase';
}

/** Coinbase pastes its secret with literal `\n`, which has to become a real newline before saving. */
export function normalizeApiSecret(location: string, secret: string): string {
  return isCoinbase(location) ? secret.replace(/\\n/g, '\n') : secret;
}

export function requiresApiSecret(location: string, capabilities: ExchangeCapabilities): boolean {
  return !capabilities.withoutApiSecret.includes(location);
}

export function requiresPassphrase(location: string, capabilities: ExchangeCapabilities): boolean {
  return capabilities.withPassphrase.includes(location);
}

/** The one-off history import is offered while connecting, not when editing an existing entry. */
export function showsBinanceHistoryImport(location: string, mode: string): boolean {
  return isBinance(location) && !isEditing(mode);
}

export function showsKeyWaitingTimeWarning(location: string): boolean {
  return SLOW_KEY_EXCHANGES.includes(location);
}

export function historyLimitMessage(location: string): MessageKey | undefined {
  return HISTORY_LIMIT_MESSAGES[location];
}

/**
 * The saved key and secret are shown masked until the user asks to replace them, and only then are
 * they demanded again. While masked there is nothing to validate: the stored pair still stands.
 */
export function acceptsSensitiveEdit(mode: string, editing: boolean): boolean {
  return !isEditing(mode) || editing;
}

/**
 * The fields the form's inputs bind to. The rest of the entry — the location, the mode — is carried
 * by the entry itself and never edited here.
 *
 * The three enum-typed fields keep the entry's own types rather than widening to `string`, so the
 * state can be folded back over the entry without anything having to re-narrow it.
 */
export interface ExchangeKeysFormState {
  apiKey: string;
  apiSecret: string;
  binanceHistoryStartTs?: number;
  binanceMarkets?: string[];
  gateLocation?: GateLocation;
  krakenAccountType?: KrakenAccountType;
  krakenFuturesApiKey?: string;
  krakenFuturesApiSecret?: string;
  name: string;
  newName?: string;
  okxLocation?: OkxLocation;
  passphrase?: string;
}

/**
 * The editable fields, taken out of the entry the dialog owns. The entry carries more than this —
 * the location and the mode — which the form reads but never writes.
 *
 * It has to answer the same for the same entry: `useMappedModelForm` compares what this returns
 * against the state it already holds to decide whether an outside edit is news, so a value invented
 * here would report every pass as a change and the two directions would never settle.
 */
export function toExchangeKeysFormState(entry: ExchangeKeysFormState): ExchangeKeysFormState {
  return {
    apiKey: entry.apiKey,
    apiSecret: entry.apiSecret,
    binanceHistoryStartTs: entry.binanceHistoryStartTs,
    binanceMarkets: entry.binanceMarkets,
    gateLocation: entry.gateLocation,
    krakenAccountType: entry.krakenAccountType,
    krakenFuturesApiKey: entry.krakenFuturesApiKey,
    krakenFuturesApiSecret: entry.krakenFuturesApiSecret,
    name: entry.name,
    newName: entry.newName,
    okxLocation: entry.okxLocation,
    passphrase: entry.passphrase,
  };
}

/** Everything outside the fields that decides which of them are demanded. */
export interface ExchangeKeysContext {
  readonly capabilities: ExchangeCapabilities;
  readonly editingFutures: boolean;
  readonly editingKeys: boolean;
  readonly location: string;
  readonly mode: string;
}

/**
 * Matches vuelidate's `required`: a string counts once trimmed, a list once it has an entry, and a
 * number always. Keeping the same reading is what lets the rules move without changing which forms
 * are accepted.
 */
function isPresent(value: unknown): boolean {
  if (value === undefined || value === null)
    return false;
  if (Array.isArray(value))
    return value.length > 0;
  if (typeof value === 'string')
    return value.trim().length > 0;

  return true;
}

/**
 * The rules are conditional on the exchange and the mode rather than on the values, so they are
 * added by a refinement over the whole object instead of being attached per field. The kraken
 * futures pair in particular has to see both fields at once: each is demanded only because the
 * other was filled in.
 */
export function exchangeKeysSchema(context: ExchangeKeysContext): ZodType<ExchangeKeysFormState> {
  const { capabilities, editingFutures, editingKeys, location, mode } = context;

  const sensitiveEditable = acceptsSensitiveEdit(mode, editingKeys);
  const futuresEditable = acceptsSensitiveEdit(mode, editingFutures);
  const editing = isEditing(mode);

  return z.object({
    apiKey: z.string(),
    apiSecret: z.string(),
    binanceHistoryStartTs: z.number().optional(),
    binanceMarkets: z.array(z.string()).optional(),
    // The three region/tier fields take their own enums rather than a bare string: none of them
    // carries a rule, but naming the type here is what lets the state fold back over the entry.
    gateLocation: GateLocation.optional(),
    krakenAccountType: KrakenAccountType.optional(),
    krakenFuturesApiKey: z.string().optional(),
    krakenFuturesApiSecret: z.string().optional(),
    name: z.string(),
    newName: z.string().optional(),
    okxLocation: OkxLocation.optional(),
    passphrase: z.string().optional(),
  }).superRefine((state, ctx) => {
    const demand = (required: boolean, path: keyof ExchangeKeysFormState, message: MessageKey): void => {
      if (required && !isPresent(state[path]))
        ctx.addIssue({ code: 'custom', message, path: [path] });
    };

    const nonEmpty = msg.$t('exchange_keys_form.validation.non_empty');
    const bothFutures = msg.$t('exchange_keys_form.validation.futures_both_required');
    const nameRequired = msg.$t('exchange_keys_form.name.non_empty');

    demand(sensitiveEditable, 'apiKey', nonEmpty);
    demand(sensitiveEditable && requiresApiSecret(location, capabilities), 'apiSecret', nonEmpty);
    demand(sensitiveEditable && requiresPassphrase(location, capabilities), 'passphrase', nonEmpty);

    // Each half is demanded only because the other was given, so both are read from the state in
    // front of us rather than from whatever either field last held.
    demand(futuresEditable && isPresent(state.krakenFuturesApiSecret), 'krakenFuturesApiKey', bothFutures);
    demand(futuresEditable && isPresent(state.krakenFuturesApiKey), 'krakenFuturesApiSecret', bothFutures);

    demand(isBinance(location), 'binanceMarkets', nonEmpty);
    demand(showsBinanceHistoryImport(location, mode), 'binanceHistoryStartTs', nonEmpty);
    demand(isGate(location), 'gateLocation', nonEmpty);
    demand(isOkx(location), 'okxLocation', nonEmpty);

    demand(!editing, 'name', nameRequired);
    demand(editing, 'newName', nameRequired);
  });
}
