import type { AdditionSummary } from '@/modules/accounts/use-account-addition-service';
import type { GnosisPaySafeMigration } from '@/modules/integrations/gnosis-pay/types';
import { Blockchain } from '@rotki/common';
import { none, some } from 'plainfp/option';
import { err, ok } from 'plainfp/result';
import { describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { findUntrackedSafe, readSafeAddition, type SafeMigrationPorts } from './safe-migration';

const SAFE = '0xabcdef1234567890abcdef1234567890abcdef12';

function ports(overrides: Partial<SafeMigrationPorts> = {}): SafeMigrationPorts {
  return {
    fetchMigration: vi.fn(async (): Promise<GnosisPaySafeMigration> => ({
      migrationId: 'safe-replacement-2026-06',
      untrackedAddresses: [{ address: SAFE, type: 'new' }],
    })),
    isConfigured: vi.fn(async (): Promise<boolean> => true),
    ...overrides,
  };
}

function summary(overrides: Partial<AdditionSummary> = {}): AdditionSummary {
  return { added: [], cancelled: false, failed: [], skipped: 0, ...overrides };
}

describe('modules/integrations/gnosis-pay/core/safe-migration', () => {
  describe('findUntrackedSafe', () => {
    it('should hand back the first untracked safe', async () => {
      expect(await findUntrackedSafe(ports())).toEqual(ok(some({ address: SAFE, type: 'new' })));
    });

    it('should find nothing when the migration left every safe tracked', async () => {
      const fetchMigration = vi.fn(async (): Promise<GnosisPaySafeMigration> => ({ migrationId: 'm', untrackedAddresses: [] }));

      expect(await findUntrackedSafe(ports({ fetchMigration }))).toEqual(ok(none));
    });

    it('should not ask the premium-gated endpoint when Gnosis Pay is not configured', async () => {
      const fetchMigration = vi.fn(async (): Promise<GnosisPaySafeMigration> => ({ migrationId: 'm', untrackedAddresses: [] }));

      const found = await findUntrackedSafe(ports({ fetchMigration, isConfigured: async () => false }));

      expect(found).toEqual(ok(none));
      expect(fetchMigration).not.toHaveBeenCalled();
    });

    it('should hand back a failed request as a value instead of rejecting', async () => {
      const cause = new Error('premium required');

      expect(await findUntrackedSafe(ports({ fetchMigration: async () => Promise.reject(cause) }))).toEqual(err(cause));
    });
  });

  describe('readSafeAddition', () => {
    it('should read an added safe as added', () => {
      expect(readSafeAddition(summary({ added: [{ address: SAFE, chain: Blockchain.GNOSIS }] }))).toEqual(ok(true));
    });

    it('should read a failure as its message', () => {
      const failed = [{ account: { address: SAFE, tags: null }, error: TaskFailed({ message: 'node unreachable' }) }];

      expect(readSafeAddition(summary({ failed }))).toEqual(err('node unreachable'));
    });

    it('should report nothing for a cancellation the user asked for', () => {
      expect(readSafeAddition(summary({ cancelled: true }))).toEqual(ok(false));
    });

    it('should report nothing for a skip, which the task dock already explains', () => {
      expect(readSafeAddition(summary({ skipped: 1 }))).toEqual(ok(false));
    });
  });
});
