import mitt from 'mitt';

/**
 * Signal bus for sigil analytics.
 *
 * Producers emit void signals at natural transition points.
 * Handlers in the sigil module read stores lazily to build payloads.
 */
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions -- mitt requires a type alias, not an interface
type SigilBusEvents = {
  /** Emitted after successful login — stores are populated. */
  'session:ready': void;
  /** Emitted after all balance fetches complete. */
  'balances:loaded': void;
  /** Emitted after history sync finishes. */
  'history:ready': void;
};

export const sigilBus = mitt<SigilBusEvents>();
