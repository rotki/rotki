import type { Airdrops } from '@/modules/airdrops/airdrops';
import { bigNumberify, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { flattenAirdrops, hasDetails, matchesStatus, toAirdropRows } from './airdrop-rows';

const NOW = 1_700_000_000;
const ADDRESS_A = '0xaaa';
const ADDRESS_B = '0xbbb';

function airdrops(): Airdrops {
  return {
    [ADDRESS_A]: {
      poap: [
        { assets: [1], claimed: false, event: 'devcon', link: 'https://poap', name: 'Devcon' },
      ],
      uniswap: { amount: bigNumberify(400), asset: 'UNI', claimed: true, hasDecoder: true, link: 'https://uni' },
    },
    [ADDRESS_B]: {
      cow: { amount: bigNumberify(10), asset: 'COW', claimed: false, cutoffTime: NOW - 100, hasDecoder: true, link: 'https://cow' },
    },
  };
}

/** The fixture's poap entry, as the list it has to be for the poap branch to be exercised. */
function poapSource(data: Airdrops): unknown[] {
  const value = data[ADDRESS_A].poap;
  if (!Array.isArray(value))
    throw new TypeError('fixture changed: the poap source must stay a list');

  return value;
}

describe('pages/airdrops/hasDetails', () => {
  it('should identify a poap delivery by its list of details', () => {
    expect(hasDetails([{ assets: [], event: 'e', link: 'l', name: 'n' }])).toBe(true);
  });

  it('should reject an absent or empty list', () => {
    expect(hasDetails(undefined)).toBe(false);
    expect(hasDetails([])).toBe(false);
  });
});

describe('pages/airdrops/flattenAirdrops', () => {
  it('should produce one row per address and source', () => {
    const rows = flattenAirdrops(airdrops(), []);

    expect(rows).toHaveLength(3);
    expect(rows.map(row => `${row.address}:${row.source}`)).toEqual([
      `${ADDRESS_A}:poap`,
      `${ADDRESS_A}:uniswap`,
      `${ADDRESS_B}:cow`,
    ]);
  });

  it('should treat an empty address list as every address', () => {
    expect(flattenAirdrops(airdrops(), [])).toHaveLength(3);
  });

  it('should keep only the named addresses', () => {
    const rows = flattenAirdrops(airdrops(), [ADDRESS_B]);

    expect(rows).toHaveLength(1);
    expect(rows[0].address).toBe(ADDRESS_B);
  });

  it('should carry a list-valued source through as poap details', () => {
    const poap = flattenAirdrops(airdrops(), [ADDRESS_A]).find(row => row.source === 'poap');

    expect(poap?.details).toHaveLength(1);
    expect(poap?.details?.[0].event).toBe('devcon');
  });

  it('should copy the poap details rather than aliasing the response', () => {
    const source = airdrops();
    const poap = flattenAirdrops(source, [ADDRESS_A]).find(row => row.source === 'poap');

    expect(poap?.details?.[0]).toEqual(expect.objectContaining({ event: 'devcon' }));
    expect(poap?.details?.[0]).not.toBe(poapSource(source)[0]);
  });

  it('should spread a single-valued source onto the row', () => {
    const uniswap = flattenAirdrops(airdrops(), [ADDRESS_A]).find(row => row.source === 'uniswap');

    expect(uniswap?.asset).toBe('UNI');
    expect(uniswap?.claimed).toBe(true);
  });
});

describe('pages/airdrops/matchesStatus', () => {
  const decoded = { address: ADDRESS_A, hasDecoder: true, source: 'uniswap' };

  it('should match everything on an unrecognised status, which is what an absent pill means', () => {
    expect(matchesStatus({ ...decoded, claimed: true }, '', NOW)).toBe(true);
    expect(matchesStatus({ ...decoded, claimed: true }, 'nonsense', NOW)).toBe(true);
  });

  it('should read a row with no decoder as unknown', () => {
    expect(matchesStatus({ address: ADDRESS_A, source: 'x' }, 'unknown', NOW)).toBe(true);
    expect(matchesStatus(decoded, 'unknown', NOW)).toBe(false);
  });

  it('should read a decoded unclaimed row as unclaimed', () => {
    expect(matchesStatus({ ...decoded, claimed: false }, 'unclaimed', NOW)).toBe(true);
    expect(matchesStatus({ ...decoded, claimed: true }, 'unclaimed', NOW)).toBe(false);
  });

  it('should not read an undecoded row as unclaimed', () => {
    expect(matchesStatus({ address: ADDRESS_A, claimed: false, source: 'x' }, 'unclaimed', NOW)).toBe(false);
  });

  describe('missed', () => {
    it('should match an unclaimed row whose cutoff has passed', () => {
      expect(matchesStatus({ ...decoded, claimed: false, cutoffTime: NOW - 1 }, 'missed', NOW)).toBe(true);
    });

    it('should not match while the cutoff is still ahead', () => {
      expect(matchesStatus({ ...decoded, claimed: false, cutoffTime: NOW + 1 }, 'missed', NOW)).toBe(false);
    });

    it('should not match a row with no cutoff at all', () => {
      expect(matchesStatus({ ...decoded, claimed: false }, 'missed', NOW)).toBe(false);
    });

    it('should not match a row that was claimed before the cutoff passed', () => {
      expect(matchesStatus({ ...decoded, claimed: true, cutoffTime: NOW - 1 }, 'missed', NOW)).toBe(false);
    });
  });

  it('should read a claimed row as claimed regardless of its decoder', () => {
    expect(matchesStatus({ address: ADDRESS_A, claimed: true, source: 'x' }, 'claimed', NOW)).toBe(true);
    expect(matchesStatus({ ...decoded, claimed: false }, 'claimed', NOW)).toBe(false);
  });
});

describe('pages/airdrops/toAirdropRows', () => {
  it('should index the rows from zero after filtering, not before', () => {
    const rows = toAirdropRows(airdrops(), [], 'claimed', NOW);

    expect(rows).toHaveLength(1);
    expect(rows[0].index).toBe(0);
    expect(rows[0].source).toBe('uniswap');
  });

  it('should fill in a missing amount with zero', () => {
    const poap = toAirdropRows(airdrops(), [ADDRESS_A], 'unknown', NOW)[0];

    expect(poap.source).toBe('poap');
    expect(poap.amount).toStrictEqual(Zero);
  });

  it('should keep an amount that is present', () => {
    const rows = toAirdropRows(airdrops(), [ADDRESS_B], '', NOW);

    expect(rows[0].amount.toNumber()).toBe(10);
  });

  it('should narrow by address and status together', () => {
    expect(toAirdropRows(airdrops(), [ADDRESS_A], 'missed', NOW)).toHaveLength(0);
    expect(toAirdropRows(airdrops(), [ADDRESS_B], 'missed', NOW)).toHaveLength(1);
  });
});
