import type { EvmEventSeed, OnlineEventSeed } from '../helpers/history-events-api';
import { TEST_EVENT_TIMESTAMP } from './history-events';

const A_ETH = 'ETH';
const A_DAI = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';

/** USDC on mainnet — the asset only the `gamma` event holds, used by the asset-filter tests. */
export const A_USDC = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';

/** Checksummed — the backend rejects anything else. */
export const ADDRESS_ALPHA = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';
export const ADDRESS_BETA = '0x57bF3B0f29E37619623994071C9e12091919675c';
export const ADDRESS_GAMMA = '0xDeBF20617708857ebe4F679508E7b7863a8A8EeE';

/** Notes are unique per event, so a row can be identified by the one substring it contains. */
export const NOTE_PREFIX = 'pillfilter';

/**
 * Events are spaced a minute apart rather than a second, so a date-boundary assertion never
 * depends on whether the backend treats a bound as inclusive.
 */
const MINUTE_MS = 60_000;
const base = TEST_EVENT_TIMESTAMP * 1000;

/**
 * Six events chosen so every filter dimension the pill bar exposes narrows to a different,
 * unambiguous row count. Each EVM event sits on its own transaction, so each renders as one row.
 *
 * | # | asset | protocol   | address | amount | location | entry type    | note    | offset |
 * |---|-------|------------|---------|--------|----------|---------------|---------|--------|
 * | 1 | ETH   | uniswap-v2 | alpha   | 1.5    | ethereum | evm event     | alpha   | +0m    |
 * | 2 | DAI   | uniswap-v2 | alpha   | 20     | ethereum | evm event     | beta    | +1m    |
 * | 3 | USDC  | curve      | beta    | 300    | ethereum | evm event     | gamma   | +2m    |
 * | 4 | ETH   | curve      | gamma   | 4000   | ethereum | evm event     | delta   | +3m    |
 * | 5 | ETH   | aave-v3    | beta    | 0.25   | optimism | evm event     | epsilon | +4m    |
 * | 6 | ETH   | —          | —       | 7      | kraken   | history event | zeta    | +5m    |
 */
export const pillFilterEvents: EvmEventSeed[] = [
  {
    address: ADDRESS_ALPHA,
    amount: '1.5',
    asset: A_ETH,
    counterparty: 'uniswap-v2',
    eventSubtype: 'airdrop',
    eventType: 'receive',
    location: 'ethereum',
    locationLabel: ADDRESS_ALPHA,
    notes: `${NOTE_PREFIX} alpha`,
    sequenceIndex: 0,
    timestamp: base,
    txRef: '0x1111111111111111111111111111111111111111111111111111111111111111',
  },
  {
    address: ADDRESS_ALPHA,
    amount: '20',
    asset: A_DAI,
    counterparty: 'uniswap-v2',
    eventSubtype: 'none',
    eventType: 'receive',
    location: 'ethereum',
    locationLabel: ADDRESS_ALPHA,
    notes: `${NOTE_PREFIX} beta`,
    sequenceIndex: 0,
    timestamp: base + MINUTE_MS,
    txRef: '0x2222222222222222222222222222222222222222222222222222222222222222',
  },
  {
    address: ADDRESS_BETA,
    amount: '300',
    asset: A_USDC,
    counterparty: 'curve',
    eventSubtype: 'fee',
    eventType: 'spend',
    location: 'ethereum',
    locationLabel: ADDRESS_BETA,
    notes: `${NOTE_PREFIX} gamma`,
    sequenceIndex: 0,
    timestamp: base + 2 * MINUTE_MS,
    txRef: '0x3333333333333333333333333333333333333333333333333333333333333333',
  },
  {
    address: ADDRESS_GAMMA,
    amount: '4000',
    asset: A_ETH,
    counterparty: 'curve',
    eventSubtype: 'none',
    eventType: 'receive',
    location: 'ethereum',
    locationLabel: ADDRESS_GAMMA,
    notes: `${NOTE_PREFIX} delta`,
    sequenceIndex: 0,
    timestamp: base + 3 * MINUTE_MS,
    txRef: '0x4444444444444444444444444444444444444444444444444444444444444444',
  },
  {
    address: ADDRESS_BETA,
    amount: '0.25',
    asset: A_ETH,
    counterparty: 'aave-v3',
    eventSubtype: 'none',
    eventType: 'spend',
    location: 'optimism',
    locationLabel: ADDRESS_BETA,
    notes: `${NOTE_PREFIX} epsilon`,
    sequenceIndex: 0,
    timestamp: base + 4 * MINUTE_MS,
    txRef: '0x5555555555555555555555555555555555555555555555555555555555555555',
  },
];

/**
 * The one non-EVM event. It exists so an entry-type exclusion has something to keep, and so the
 * protocol and address dimensions have a row that legitimately carries neither.
 */
export const pillFilterOnlineEvent: OnlineEventSeed = {
  amount: '7',
  asset: A_ETH,
  eventSubtype: 'airdrop',
  eventType: 'receive',
  groupIdentifier: 'pillfilter-online-1',
  location: 'kraken',
  notes: `${NOTE_PREFIX} zeta`,
  sequenceIndex: 0,
  timestamp: base + 5 * MINUTE_MS,
};

/** Chain id each seeded transaction must be inserted under, keyed by its hash. */
export const pillFilterChainIds: Record<string, number> = {
  '0x1111111111111111111111111111111111111111111111111111111111111111': 1,
  '0x2222222222222222222222222222222222222222222222222222222222222222': 1,
  '0x3333333333333333333333333333333333333333333333333333333333333333': 1,
  '0x4444444444444444444444444444444444444444444444444444444444444444': 1,
  '0x5555555555555555555555555555555555555555555555555555555555555555': 10,
};

export const TOTAL_SEEDED_EVENTS = pillFilterEvents.length + 1;

/**
 * `DD MM YYYY HH mm ss` typed into the date picker: 15/01/2024 12:02:30 UTC, i.e. two and a half
 * minutes past the first event. Playwright pins the browser to UTC, so this is unambiguous.
 */
export const DATE_CUTOFF_DIGITS = '15012024120230';

/** Events after `DATE_CUTOFF_DIGITS`: delta (+3m), epsilon (+4m) and zeta (+5m). */
export const EVENTS_AFTER_CUTOFF = 3;

/** The same cutoff written the way a user types it into the bar, in the default date format. */
export const DATE_CUTOFF_TYPED = '15/01/2024 12:02:30';

/**
 * A bulk set for the pagination tests, seeded into its own user so it cannot disturb the row
 * counts above. Plain history events need no transaction, so they are cheap to generate.
 *
 * 24 events over 3 pages at the default 10 per page, of which only 4 are on kraken — few enough
 * that filtering to them cannot land on a later page, which is what makes the page-reset
 * assertion meaningful.
 */
export const PAGED_TOTAL = 24;
export const PAGED_KRAKEN = 4;
export const PAGE_SIZE = 10;

export function pagedEvents(): OnlineEventSeed[] {
  return Array.from({ length: PAGED_TOTAL }, (_, index) => ({
    amount: '1',
    asset: A_ETH,
    eventSubtype: 'none',
    eventType: 'receive',
    groupIdentifier: `pillfilter-paged-${index}`,
    location: index < PAGED_KRAKEN ? 'kraken' : 'coinbase',
    notes: `${NOTE_PREFIX} paged ${index}`,
    sequenceIndex: 0,
    timestamp: base + index * MINUTE_MS,
  }));
}

/** USDC on Optimism — same symbol as {@link A_USDC}, different chain. */
export const A_USDC_OPTIMISM = 'eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85';

/**
 * Two events holding assets that render with the *same* symbol on different chains, which is
 * what the asset icon, caption and chain badge exist to tell apart. Seeded into their own user
 * so they cannot shift the location counts in the main set.
 */
export const multiChainEvents: EvmEventSeed[] = [
  {
    amount: '11',
    asset: A_USDC,
    counterparty: 'curve',
    eventSubtype: 'none',
    eventType: 'receive',
    location: 'ethereum',
    notes: `${NOTE_PREFIX} usdc mainnet`,
    sequenceIndex: 0,
    timestamp: base,
    txRef: '0x7777777777777777777777777777777777777777777777777777777777777777',
  },
  {
    amount: '22',
    asset: A_USDC_OPTIMISM,
    counterparty: 'curve',
    eventSubtype: 'none',
    eventType: 'receive',
    location: 'optimism',
    notes: `${NOTE_PREFIX} usdc optimism`,
    sequenceIndex: 0,
    timestamp: base + MINUTE_MS,
    txRef: '0x8888888888888888888888888888888888888888888888888888888888888888',
  },
];

export const multiChainChainIds: Record<string, number> = {
  '0x7777777777777777777777777777777777777777777777777777777777777777': 1,
  '0x8888888888888888888888888888888888888888888888888888888888888888': 10,
};
