import type { MissingAcquisition } from '@/modules/reports/report-types';
import { assert, type BigNumber } from '@rotki/common';
import { bigNumberSum } from '@/modules/core/common/data/calculation';

/** One asset's missing acquisitions, collapsed into the row the table shows. */
export interface GroupedMissingAcquisition {
  readonly asset: string;
  readonly startDate: number;
  readonly endDate: number;
  readonly totalAmountMissing: BigNumber;
  readonly acquisitions: MissingAcquisition[];
}

/**
 * Collapses the report's missing acquisitions into one row per asset.
 *
 * @remarks
 * Each row carries the period the gaps span and how much is missing across all of them, so the
 * table can be read without expanding it. The acquisitions within a row are ordered oldest first,
 * which is what makes the first and last of them the period's bounds.
 *
 * @param items - every missing acquisition the report reported, in any order
 * @returns one row per asset, in the order the assets first appear
 */
export function groupMissingAcquisitions(items: MissingAcquisition[]): GroupedMissingAcquisition[] {
  const grouped: Record<string, MissingAcquisition[]> = {};

  for (const item of items) {
    if (grouped[item.asset])
      grouped[item.asset].push(item);
    else grouped[item.asset] = [item];
  }

  return Object.keys(grouped).map((asset) => {
    const acquisitions = grouped[asset].sort((a, b) => a.time - b.time);
    const endDate = acquisitions.at(-1)?.time;
    assert(endDate, 'end date is missing');

    return {
      acquisitions,
      asset,
      endDate,
      startDate: acquisitions[0].time,
      totalAmountMissing: bigNumberSum(acquisitions.map(({ missingAmount }) => missingAmount)),
    };
  });
}
