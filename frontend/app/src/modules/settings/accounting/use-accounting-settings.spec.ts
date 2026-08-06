import type {
  AccountingRuleConflictRequestPayload,
  AccountingRuleRequestPayload,
} from '@/modules/settings/types/accounting';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { useAccountingSettings } from './use-accounting-settings';

const rulePayload: AccountingRuleRequestPayload = { limit: 10, offset: 0 };
const conflictPayload: AccountingRuleConflictRequestPayload = { limit: 10, offset: 0 };

const fetchAccountingRule = vi.fn();
const fetchAccountingRules = vi.fn();
const fetchAccountingRuleConflicts = vi.fn();
const resolveAccountingRuleConflictsCaller = vi.fn();
const exportAccountingRules = vi.fn();
const importAccountingRulesData = vi.fn();
const uploadAccountingRulesData = vi.fn();
const resetAccountingRules = vi.fn();

const notifyError = vi.fn();
const showErrorMessage = vi.fn();
const showSuccessMessage = vi.fn();

const runTaskResult = vi.fn();
const downloadFileByTextContent = vi.fn();

const submitTask = vi.fn(runSpecWith(runTaskResult));

const openDirectory = vi.fn();
const getPath = vi.fn();
let appSession = false;

vi.mock('@/modules/settings/api/use-accounting-api', () => ({
  useAccountingApi: (): object => ({
    exportAccountingRules,
    fetchAccountingRule,
    fetchAccountingRuleConflicts,
    fetchAccountingRules,
    importAccountingRulesData,
    resetAccountingRules,
    resolveAccountingRuleConflicts: resolveAccountingRuleConflictsCaller,
    uploadAccountingRulesData,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (error: unknown): string => error instanceof Error ? error.message : String(error),
  useNotifications: (): object => ({ notifyError, showErrorMessage, showSuccessMessage }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): object => ({ cancelByType: (): (() => void) => vi.fn(), runTaskResult, statusOf: vi.fn(), submitTask }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): object => ({ appSession, getPath, openDirectory }),
}));

vi.mock('@/modules/core/common/file/download', () => ({
  downloadFileByTextContent: (...args: unknown[]): void => downloadFileByTextContent(...args),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

const actionableFailure = err(TaskFailed({ message: 'boom' }));
const cancelledFailure = err(Cancelled({ message: '' }));

const collectionResponse = {
  entries: [{ identifier: 1 }],
  entriesFound: 1,
  entriesLimit: 10,
  entriesTotal: 1,
};

describe('useAccountingSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    appSession = false;
  });

  describe('getAccountingRule', () => {
    it('should return the fetched rule', async () => {
      fetchAccountingRule.mockResolvedValue({ identifier: 1 });
      const result = await useAccountingSettings().getAccountingRule(rulePayload, 'uniswap');
      expect(result).toEqual({ identifier: 1 });
    });

    it('should map a null result to undefined', async () => {
      fetchAccountingRule.mockResolvedValue(null);
      const result = await useAccountingSettings().getAccountingRule(rulePayload, null);
      expect(result).toBeUndefined();
    });

    it('should notify and return undefined on error', async () => {
      fetchAccountingRule.mockRejectedValue(new Error('nope'));
      const result = await useAccountingSettings().getAccountingRule(rulePayload, null);
      expect(result).toBeUndefined();
      expect(notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('getAccountingRules', () => {
    it('should map the collection response', async () => {
      fetchAccountingRules.mockResolvedValue(collectionResponse);
      const result = await useAccountingSettings().getAccountingRules(rulePayload);
      expect(result).toMatchObject({ data: [{ identifier: 1 }], found: 1, limit: 10, total: 1 });
    });

    it('should notify and return an empty collection on error', async () => {
      fetchAccountingRules.mockRejectedValue(new Error('nope'));
      const result = await useAccountingSettings().getAccountingRules(rulePayload);
      expect(result.data).toEqual([]);
      expect(notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('getAccountingRulesConflicts', () => {
    it('should map the collection response', async () => {
      fetchAccountingRuleConflicts.mockResolvedValue(collectionResponse);
      const result = await useAccountingSettings().getAccountingRulesConflicts(conflictPayload);
      expect(result.total).toBe(1);
    });

    it('should notify and return an empty collection on error', async () => {
      fetchAccountingRuleConflicts.mockRejectedValue(new Error('nope'));
      const result = await useAccountingSettings().getAccountingRulesConflicts(conflictPayload);
      expect(result.data).toEqual([]);
      expect(notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('resolveAccountingRuleConflicts', () => {
    it('should return success when the call resolves', async () => {
      resolveAccountingRuleConflictsCaller.mockResolvedValue(undefined);
      const result = await useAccountingSettings().resolveAccountingRuleConflicts({ conflicts: [] });
      expect(result).toEqual({ success: true });
    });

    it('should return the error message when the call rejects', async () => {
      resolveAccountingRuleConflictsCaller.mockRejectedValue(new Error('bad'));
      const result = await useAccountingSettings().resolveAccountingRuleConflicts({ conflicts: [] });
      expect(result).toEqual({ message: 'bad', success: false });
    });
  });

  describe('exportJSON', () => {
    it('should download the exported rules in a web session', async () => {
      appSession = false;
      runTaskResult.mockResolvedValue(ok({ rules: [] }));
      await useAccountingSettings().exportJSON();
      expect(downloadFileByTextContent).toHaveBeenCalledOnce();
    });

    it('should abort when no directory is selected in an app session', async () => {
      appSession = true;
      openDirectory.mockResolvedValue(undefined);
      await useAccountingSettings().exportJSON();
      expect(submitTask).not.toHaveBeenCalled();
      expect(downloadFileByTextContent).not.toHaveBeenCalled();
    });

    it('should show a success message in an app session', async () => {
      appSession = true;
      openDirectory.mockResolvedValue('/tmp');
      runTaskResult.mockResolvedValue(ok(true));
      await useAccountingSettings().exportJSON();
      expect(showSuccessMessage).toHaveBeenCalledOnce();
    });

    it('should show an error message when the app-session export fails', async () => {
      appSession = true;
      openDirectory.mockResolvedValue('/tmp');
      runTaskResult.mockResolvedValue(ok(false));
      await useAccountingSettings().exportJSON();
      expect(showErrorMessage).toHaveBeenCalledOnce();
    });

    it('should stop silently when the export task is not actionable', async () => {
      appSession = false;
      runTaskResult.mockResolvedValue(cancelledFailure);
      await useAccountingSettings().exportJSON();
      expect(downloadFileByTextContent).not.toHaveBeenCalled();
      expect(showErrorMessage).not.toHaveBeenCalled();
    });
  });

  describe('importJSON', () => {
    const file = new File(['{}'], 'rules.json');

    it('should import via path when interop resolves one', async () => {
      getPath.mockReturnValue('/tmp/rules.json');
      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return ok(true);
      });
      const result = await useAccountingSettings().importJSON(file);
      expect(importAccountingRulesData).toHaveBeenCalledWith('/tmp/rules.json');
      expect(result).toEqual({ message: '', success: true });
    });

    it('should upload the file when no path is available', async () => {
      getPath.mockReturnValue(undefined);
      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return ok(true);
      });
      await useAccountingSettings().importJSON(file);
      expect(uploadAccountingRulesData).toHaveBeenCalledWith(file);
    });

    it('should return the failure message on an actionable failure', async () => {
      getPath.mockReturnValue(undefined);
      runTaskResult.mockResolvedValue(actionableFailure);
      const result = await useAccountingSettings().importJSON(file);
      expect(result).toEqual({ message: 'boom', success: false });
    });

    it('should return null on a non-actionable failure', async () => {
      getPath.mockReturnValue(undefined);
      runTaskResult.mockResolvedValue(cancelledFailure);
      const result = await useAccountingSettings().importJSON(file);
      expect(result).toBeNull();
    });
  });

  describe('resetToDefaults', () => {
    it('should show a success message and return success', async () => {
      runTaskResult.mockResolvedValue(ok(true));
      const result = await useAccountingSettings().resetToDefaults();
      expect(showSuccessMessage).toHaveBeenCalledOnce();
      expect(result).toEqual({ message: '', success: true });
    });

    it('should show an error message on an actionable failure', async () => {
      runTaskResult.mockResolvedValue(actionableFailure);
      const result = await useAccountingSettings().resetToDefaults();
      expect(showErrorMessage).toHaveBeenCalledOnce();
      expect(result).toEqual({ message: 'boom', success: false });
    });

    it('should return null on a non-actionable failure', async () => {
      runTaskResult.mockResolvedValue(cancelledFailure);
      const result = await useAccountingSettings().resetToDefaults();
      expect(result).toBeNull();
    });
  });
});
