import type { MissingAcquisition } from '@/modules/reports/report-types';
import { bigNumberify, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { groupMissingAcquisitions } from '@/modules/reports/missing-acquisitions';

function acquisition(asset: string, time: number, missingAmount = '1'): MissingAcquisition {
  return {
    asset,
    foundAmount: Zero,
    missingAmount: bigNumberify(missingAmount),
    time,
  };
}

describe('groupMissingAcquisitions', () => {
  it('should return nothing for an empty report', () => {
    expect(groupMissingAcquisitions([])).toEqual([]);
  });

  it('should collapse every gap in one asset into a single row', () => {
    const grouped = groupMissingAcquisitions([
      acquisition('ETH', 10),
      acquisition('ETH', 20),
      acquisition('ETH', 30),
    ]);

    expect(grouped).toHaveLength(1);
    expect(grouped[0].acquisitions).toHaveLength(3);
  });

  it('should keep the assets apart', () => {
    const grouped = groupMissingAcquisitions([
      acquisition('ETH', 10),
      acquisition('BTC', 20),
      acquisition('ETH', 30),
    ]);

    expect(grouped.map(row => row.asset)).toEqual(['ETH', 'BTC']);
    expect(grouped[0].acquisitions).toHaveLength(2);
    expect(grouped[1].acquisitions).toHaveLength(1);
  });

  it('should order the rows by the asset first seen', () => {
    const grouped = groupMissingAcquisitions([acquisition('BTC', 30), acquisition('ETH', 10)]);

    expect(grouped.map(row => row.asset)).toEqual(['BTC', 'ETH']);
  });

  describe('the period a row spans', () => {
    it('should read the bounds from the oldest and newest gap', () => {
      const grouped = groupMissingAcquisitions([
        acquisition('ETH', 30),
        acquisition('ETH', 10),
        acquisition('ETH', 20),
      ]);

      expect(grouped[0].startDate).toBe(10);
      expect(grouped[0].endDate).toBe(30);
    });

    it('should give a single gap the same start and end', () => {
      const grouped = groupMissingAcquisitions([acquisition('ETH', 42)]);

      expect(grouped[0].startDate).toBe(42);
      expect(grouped[0].endDate).toBe(42);
    });

    it('should order the acquisitions oldest first whatever order they arrived in', () => {
      const grouped = groupMissingAcquisitions([
        acquisition('ETH', 30),
        acquisition('ETH', 10),
        acquisition('ETH', 20),
      ]);

      expect(grouped[0].acquisitions.map(item => item.time)).toEqual([10, 20, 30]);
    });
  });

  describe('the amount a row is missing', () => {
    it('should add up every gap in the asset', () => {
      const grouped = groupMissingAcquisitions([
        acquisition('ETH', 10, '1.5'),
        acquisition('ETH', 20, '2.25'),
      ]);

      expect(grouped[0].totalAmountMissing.toString()).toBe('3.75');
    });

    it('should not mix the assets together', () => {
      const grouped = groupMissingAcquisitions([
        acquisition('ETH', 10, '1'),
        acquisition('BTC', 20, '5'),
      ]);

      expect(grouped[0].totalAmountMissing.toString()).toBe('1');
      expect(grouped[1].totalAmountMissing.toString()).toBe('5');
    });
  });
});
