import type { ManualBalanceWithValue, RawManualBalance } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { Status } from '@/modules/core/common/status';
import { useManualBalances } from './use-manual-balances';

const manualBalances = ref<ManualBalanceWithValue[]>([]);
const manualLiabilities = ref<ManualBalanceWithValue[]>([]);

const notifyError = vi.fn();
const showErrorMessage = vi.fn();
const runTask = vi.fn();
const cancelTaskByTaskType = vi.fn().mockResolvedValue(undefined);
const fetchDisabled = vi.fn().mockReturnValue(false);
const getStatus = vi.fn().mockReturnValue(Status.NONE);
const setStatus = vi.fn();
const resetStatus = vi.fn();
const queryManualBalances = vi.fn();
const addManualBalances = vi.fn();
const editManualBalances = vi.fn();
const deleteManualBalances = vi.fn();
const valueThreshold = ref<string | undefined>('0');

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn(() => ({ manualBalances, manualLiabilities })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError, showErrorMessage })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useTaskHandler: vi.fn(() => ({ cancelTaskByTaskType, runTask })),
  };
});

vi.mock('@/modules/shell/sync-progress/use-status-updater', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useStatusUpdater: vi.fn(() => ({ fetchDisabled, getStatus, resetStatus, setStatus })),
  };
});

vi.mock('@/modules/balances/api/use-manual-balances-api', () => ({
  useManualBalancesApi: vi.fn(() => ({
    addManualBalances,
    deleteManualBalances,
    editManualBalances,
    queryManualBalances,
  })),
}));

vi.mock('@/modules/assets/amount-display/use-usd-value-threshold', () => ({
  useValueThreshold: vi.fn(() => valueThreshold),
}));

interface RawBalanceJson {
  amount: string;
  asset: string;
  balanceType: BalanceType;
  identifier: number;
  label: string;
  location: string;
  tags: string[] | null;
  value: string;
}

function makeBalanceJson(overrides: Partial<RawBalanceJson> = {}): RawBalanceJson {
  return {
    amount: '1',
    asset: 'ETH',
    balanceType: BalanceType.ASSET,
    identifier: 1,
    label: 'test',
    location: 'external',
    tags: null,
    value: '1',
    ...overrides,
  };
}

function makeBalance(overrides: Partial<ManualBalanceWithValue> = {}): ManualBalanceWithValue {
  return {
    amount: bigNumberify(1),
    asset: 'ETH',
    balanceType: BalanceType.ASSET,
    identifier: 1,
    label: 'test',
    location: 'external',
    tags: null,
    value: bigNumberify(1),
    ...overrides,
  };
}

function makeRawBalance(overrides: Partial<RawManualBalance> = {}): RawManualBalance {
  return {
    amount: bigNumberify(1),
    asset: 'ETH',
    balanceType: BalanceType.ASSET,
    label: 'raw',
    location: 'external',
    tags: null,
    ...overrides,
  };
}

describe('useManualBalances', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(manualBalances, []);
    set(manualLiabilities, []);
    set(valueThreshold, '0');
    fetchDisabled.mockReturnValue(false);
    getStatus.mockReturnValue(Status.NONE);
  });

  describe('fetchManualBalances', () => {
    it('should skip the fetch when fetchDisabled returns true', async () => {
      fetchDisabled.mockReturnValue(true);

      await useManualBalances().fetchManualBalances();

      expect(runTask).not.toHaveBeenCalled();
      expect(setStatus).not.toHaveBeenCalled();
    });

    it('should set REFRESHING when status is already LOADED', async () => {
      getStatus.mockReturnValue(Status.LOADED);
      runTask.mockResolvedValue({ success: true, result: { balances: [] } });

      await useManualBalances().fetchManualBalances();

      expect(setStatus).toHaveBeenNthCalledWith(1, Status.REFRESHING);
      expect(setStatus).toHaveBeenLastCalledWith(Status.LOADED);
    });

    it('should split assets and liabilities into the matching refs', async () => {
      const asset = makeBalanceJson({ asset: 'ETH', balanceType: BalanceType.ASSET, identifier: 1 });
      const liability = makeBalanceJson({ asset: 'DAI', balanceType: BalanceType.LIABILITY, identifier: 2 });
      runTask.mockResolvedValue({ success: true, result: { balances: [asset, liability] } });

      await useManualBalances().fetchManualBalances();

      expect(get(manualBalances)).toHaveLength(1);
      expect(get(manualBalances)[0].asset).toBe('ETH');
      expect(get(manualLiabilities)).toHaveLength(1);
      expect(get(manualLiabilities)[0].asset).toBe('DAI');
    });

    it('should notify on actionable failure and reset status', async () => {
      runTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: false,
        error: new Error('boom'),
        message: 'boom',
        skipped: false,
        success: false,
      });

      await useManualBalances().fetchManualBalances();

      expect(notifyError).toHaveBeenCalled();
      expect(resetStatus).toHaveBeenCalled();
    });

    it('should not notify when the failure was cancelled', async () => {
      runTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: true,
        message: '',
        skipped: false,
        success: false,
      });

      await useManualBalances().fetchManualBalances();

      expect(notifyError).not.toHaveBeenCalled();
      expect(resetStatus).toHaveBeenCalled();
    });

    it('should forward the value threshold to queryManualBalances', async () => {
      set(valueThreshold, '5');
      runTask.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return { success: true, result: { balances: [] } };
      });

      await useManualBalances().fetchManualBalances();

      expect(queryManualBalances).toHaveBeenCalledWith('5');
    });
  });

  describe('addManualBalance', () => {
    it('should cancel any in-flight fetch before adding', async () => {
      runTask.mockResolvedValue({ success: true, result: { balances: [] } });

      await useManualBalances().addManualBalance(makeRawBalance());

      expect(cancelTaskByTaskType).toHaveBeenCalled();
    });

    it('should update balances and return success on a successful add', async () => {
      const created = makeBalanceJson({ identifier: 10, label: 'added' });
      runTask.mockResolvedValue({ success: true, result: { balances: [created] } });

      const result = await useManualBalances().addManualBalance(makeRawBalance());

      expect(result).toEqual({ success: true });
      expect(get(manualBalances)).toHaveLength(1);
      expect(get(manualBalances)[0].identifier).toBe(10);
    });

    it('should extract validation errors when the failure carries ApiValidationError', async () => {
      const error = new ApiValidationError('{"label": ["already exists"]}');
      runTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: false,
        error,
        message: 'validation failed',
        skipped: false,
        success: false,
      });

      const result = await useManualBalances().addManualBalance(makeRawBalance({ label: 'dup' }));

      expect(result).toEqual({ message: { label: ['already exists'] }, success: false });
    });

    it('should return the raw message on a non-validation failure', async () => {
      runTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: false,
        error: new Error('boom'),
        message: 'server exploded',
        skipped: false,
        success: false,
      });

      const result = await useManualBalances().addManualBalance(makeRawBalance());

      expect(result).toEqual({ message: 'server exploded', success: false });
    });

    it('should return an empty message when the failure is cancelled', async () => {
      runTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: true,
        message: 'cancelled',
        skipped: false,
        success: false,
      });

      const result = await useManualBalances().addManualBalance(makeRawBalance());

      expect(result).toEqual({ message: '', success: false });
    });
  });

  describe('editManualBalance', () => {
    it('should update balances and return success on a successful edit', async () => {
      const updatedJson = makeBalanceJson({ identifier: 3, label: 'updated' });
      runTask.mockResolvedValue({ success: true, result: { balances: [updatedJson] } });

      const result = await useManualBalances().editManualBalance(makeBalance({ identifier: 3, label: 'updated' }));

      expect(result).toEqual({ success: true });
      expect(get(manualBalances)[0].label).toBe('updated');
    });

    it('should extract validation errors on ApiValidationError failure', async () => {
      const error = new ApiValidationError('{"amount": ["must be positive"]}');
      runTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: false,
        error,
        message: 'validation failed',
        skipped: false,
        success: false,
      });

      const result = await useManualBalances().editManualBalance(makeBalance({ amount: bigNumberify(-1) }));

      expect(result).toEqual({ message: { amount: ['must be positive'] }, success: false });
    });
  });

  describe('save', () => {
    it('should route raw balances (no identifier) to addManualBalance', async () => {
      runTask.mockResolvedValue({ success: true, result: { balances: [] } });

      await useManualBalances().save(makeRawBalance());

      expect(runTask).toHaveBeenCalledWith(expect.any(Function), expect.objectContaining({ type: expect.any(Number) }));
      expect(addManualBalances).toBeDefined();
    });

    it('should route balances with an identifier to editManualBalance', async () => {
      runTask.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return { success: true, result: { balances: [] } };
      });

      await useManualBalances().save(makeBalance({ identifier: 7 }));

      expect(editManualBalances).toHaveBeenCalled();
      expect(addManualBalances).not.toHaveBeenCalled();
    });
  });

  describe('deleteManualBalance', () => {
    it('should update balances on success', async () => {
      const remaining = makeBalance({ identifier: 2, label: 'kept' });
      deleteManualBalances.mockResolvedValue({ balances: [remaining] });

      await useManualBalances().deleteManualBalance(1);

      expect(deleteManualBalances).toHaveBeenCalledWith([1]);
      expect(get(manualBalances)).toHaveLength(1);
      expect(get(manualBalances)[0].identifier).toBe(2);
      expect(showErrorMessage).not.toHaveBeenCalled();
    });

    it('should surface an error message when the API rejects', async () => {
      deleteManualBalances.mockRejectedValue(new Error('nope'));

      await useManualBalances().deleteManualBalance(1);

      expect(showErrorMessage).toHaveBeenCalled();
      const [, message] = showErrorMessage.mock.calls[0];
      expect(message).toContain('nope');
    });
  });
});
