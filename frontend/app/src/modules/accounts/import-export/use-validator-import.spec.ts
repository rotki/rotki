import type { CSVRow } from '@/modules/accounts/import-export/account-csv-schema';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  save: vi.fn(),
}));

vi.mock('@/modules/accounts/blockchain/use-account-manage', () => ({
  useAccountManage: vi.fn(() => ({ save: mocks.save })),
}));

async function importModule(): Promise<typeof import('./use-validator-import')> {
  return import('./use-validator-import');
}

function row(publicKey: string): CSVRow {
  return {
    address: publicKey,
    addressExtras: { ownershipPercentage: '100' },
    chain: 'eth2',
    label: '',
    tags: [],
  };
}

describe('useValidatorImport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.save.mockResolvedValue(true);
  });

  it('should save every validator in the file', async () => {
    const { useValidatorImport } = await importModule();

    await useValidatorImport().importValidators([row('0xaaa'), row('0xbbb')], vi.fn());

    expect(mocks.save).toHaveBeenCalledTimes(2);
    expect(mocks.save.mock.calls.map(([action]) => action.data.publicKey)).toStrictEqual(['0xaaa', '0xbbb']);
  });

  it('should save them one at a time', async () => {
    let active = 0;
    let maxActive = 0;
    mocks.save.mockImplementation(async () => {
      active += 1;
      maxActive = Math.max(maxActive, active);
      await Promise.resolve();
      active -= 1;
      return true;
    });
    const { useValidatorImport } = await importModule();

    await useValidatorImport().importValidators([row('0xaaa'), row('0xbbb'), row('0xccc')], vi.fn());

    expect(maxActive).toBe(1);
  });

  it('should count a validator only once it has been saved, so the bar never runs ahead', async () => {
    const seen: number[] = [];
    let progress = 0;
    mocks.save.mockImplementation(async () => {
      seen.push(progress);
      return true;
    });
    const { useValidatorImport } = await importModule();

    await useValidatorImport().importValidators([row('0xaaa'), row('0xbbb')], () => {
      progress += 1;
    });

    // Each save observes only the validators finished before it.
    expect(seen).toStrictEqual([0, 1]);
    expect(progress).toBe(2);
  });

  it('should attempt a duplicated public key rather than dropping it', async () => {
    const { useValidatorImport } = await importModule();

    await useValidatorImport().importValidators([row('0xaaa'), row('0xaaa')], vi.fn());

    expect(mocks.save).toHaveBeenCalledTimes(2);
  });
});
