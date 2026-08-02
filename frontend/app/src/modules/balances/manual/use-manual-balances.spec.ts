import type { ManualBalanceWithValue, RawManualBalance } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useManualBalances } from './use-manual-balances';

const manualBalances = ref<ManualBalanceWithValue[]>([]);
const manualLiabilities = ref<ManualBalanceWithValue[]>([]);

const notifyError = vi.fn();
const showErrorMessage = vi.fn();
const runTaskResult = vi.fn();
const cancelActivity = vi.fn();
const statusOf = vi.fn();

/** Runs the submitted spec inline so assertions see the real `run` body. */
const submitTask = vi.fn(runSpecWith(runTaskResult));

const IDLE = { active: false, everCompleted: false, pending: false, running: false };
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

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelActivity,
    cancelByType: vi.fn(() => vi.fn()),
    runTaskResult,
    statusOf,
    submitTask,
  })),
}));

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
    statusOf.mockReturnValue(IDLE);
  });

  describe('fetchManualBalances', () => {
    it('should skip the fetch when already completed and not user initiated', async () => {
      statusOf.mockReturnValue({ ...IDLE, everCompleted: true });

      await useManualBalances().fetchManualBalances();

      expect(submitTask).not.toHaveBeenCalled();
    });

    it('should skip the fetch while one is already active', async () => {
      statusOf.mockReturnValue({ ...IDLE, active: true, running: true });

      await useManualBalances().fetchManualBalances();

      expect(submitTask).not.toHaveBeenCalled();
    });

    it('should fetch when user initiated even if already completed', async () => {
      statusOf.mockReturnValue({ ...IDLE, everCompleted: true });
      runTaskResult.mockResolvedValue(ok({ balances: [] }));

      await useManualBalances().fetchManualBalances(true);

      expect(submitTask).toHaveBeenCalledOnce();
    });

    it('should split assets and liabilities into the matching refs', async () => {
      const asset = makeBalanceJson({ asset: 'ETH', balanceType: BalanceType.ASSET, identifier: 1 });
      const liability = makeBalanceJson({ asset: 'DAI', balanceType: BalanceType.LIABILITY, identifier: 2 });
      runTaskResult.mockResolvedValue(ok({ balances: [asset, liability] }));

      await useManualBalances().fetchManualBalances();

      expect(get(manualBalances)).toHaveLength(1);
      expect(get(manualBalances)[0].asset).toBe('ETH');
      expect(get(manualLiabilities)).toHaveLength(1);
      expect(get(manualLiabilities)[0].asset).toBe('DAI');
    });

    it('should notify on an actionable failure', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ cause: new Error('boom'), message: 'boom' })));

      await useManualBalances().fetchManualBalances();

      expect(notifyError).toHaveBeenCalled();
    });

    it('should not notify when the failure was cancelled', async () => {
      runTaskResult.mockResolvedValue(err(Cancelled({ message: '' })));

      await useManualBalances().fetchManualBalances();

      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should forward the value threshold to queryManualBalances', async () => {
      set(valueThreshold, '5');
      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return ok({ balances: [] });
      });

      await useManualBalances().fetchManualBalances();

      expect(queryManualBalances).toHaveBeenCalledWith('5');
    });
  });

  describe('addManualBalance', () => {
    it('should cancel any in-flight fetch before adding', async () => {
      runTaskResult.mockResolvedValue(ok({ balances: [] }));

      await useManualBalances().addManualBalance(makeRawBalance());

      expect(cancelActivity).toHaveBeenCalledWith(ActivityKind.MANUAL_BALANCES, ActivityPart.FETCH);
    });

    it('should give each balance its own activity id so concurrent saves do not dedup', async () => {
      runTaskResult.mockResolvedValue(ok({ balances: [] }));

      const balances = useManualBalances();
      await balances.addManualBalance(makeRawBalance({ asset: 'ETH', label: 'one' }));
      await balances.addManualBalance(makeRawBalance({ asset: 'DAI', label: 'two' }));

      const [first] = submitTask.mock.calls[0];
      const [second] = submitTask.mock.calls[1];
      expect(first.id).not.toBe(second.id);
    });

    it('should update balances and return success on a successful add', async () => {
      const created = makeBalanceJson({ identifier: 10, label: 'added' });
      runTaskResult.mockResolvedValue(ok({ balances: [created] }));

      const result = await useManualBalances().addManualBalance(makeRawBalance());

      expect(result).toEqual({ success: true });
      expect(get(manualBalances)).toHaveLength(1);
      expect(get(manualBalances)[0].identifier).toBe(10);
    });

    it('should extract validation errors when the failure carries ApiValidationError', async () => {
      const error = new ApiValidationError('{"label": ["already exists"]}');
      runTaskResult.mockResolvedValue(err(TaskFailed({ cause: error, message: 'validation failed' })));

      const result = await useManualBalances().addManualBalance(makeRawBalance({ label: 'dup' }));

      expect(result).toEqual({ message: { label: ['already exists'] }, success: false });
    });

    it('should return the raw message on a non-validation failure', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ cause: new Error('boom'), message: 'server exploded' })));

      const result = await useManualBalances().addManualBalance(makeRawBalance());

      expect(result).toEqual({ message: 'server exploded', success: false });
    });

    it('should return an empty message when the failure is cancelled', async () => {
      runTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      const result = await useManualBalances().addManualBalance(makeRawBalance());

      expect(result).toEqual({ message: '', success: false });
    });
  });

  describe('editManualBalance', () => {
    it('should update balances and return success on a successful edit', async () => {
      const updatedJson = makeBalanceJson({ identifier: 3, label: 'updated' });
      runTaskResult.mockResolvedValue(ok({ balances: [updatedJson] }));

      const result = await useManualBalances().editManualBalance(makeBalance({ identifier: 3, label: 'updated' }));

      expect(result).toEqual({ success: true });
      expect(get(manualBalances)[0].label).toBe('updated');
    });

    it('should key the activity id on the balance identifier', async () => {
      runTaskResult.mockResolvedValue(ok({ balances: [] }));

      await useManualBalances().editManualBalance(makeBalance({ identifier: 42 }));

      const [spec] = submitTask.mock.calls[0];
      expect(spec.id).toContain('42');
    });

    it('should extract validation errors on ApiValidationError failure', async () => {
      const error = new ApiValidationError('{"amount": ["must be positive"]}');
      runTaskResult.mockResolvedValue(err(TaskFailed({ cause: error, message: 'validation failed' })));

      const result = await useManualBalances().editManualBalance(makeBalance({ amount: bigNumberify(-1) }));

      expect(result).toEqual({ message: { amount: ['must be positive'] }, success: false });
    });
  });

  describe('save', () => {
    it('should route raw balances (no identifier) to addManualBalance', async () => {
      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return ok({ balances: [] });
      });

      await useManualBalances().save(makeRawBalance());

      expect(addManualBalances).toHaveBeenCalled();
      expect(editManualBalances).not.toHaveBeenCalled();
    });

    it('should route balances with an identifier to editManualBalance', async () => {
      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return ok({ balances: [] });
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
