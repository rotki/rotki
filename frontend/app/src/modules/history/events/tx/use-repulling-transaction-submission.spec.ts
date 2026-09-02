import type { Exchange } from '@/modules/balances/types/exchanges';
import type { RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import type { RepullingTransactionResult } from '@/modules/history/events/tx/use-history-transactions';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, ref } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { type RepullingFormHandle, useRepullingTransactionSubmission } from './use-repulling-transaction-submission';

const {
  createDefaultFormData,
  repullingEthStakingEvents,
  repullingExchangeEvents,
  repullingTransactions,
  resetUndecodedTransactionsStatus,
  setMessage,
  shouldShowConfirmation,
  show,
} = vi.hoisted(() => ({
  createDefaultFormData: vi.fn(),
  repullingEthStakingEvents: vi.fn(),
  repullingExchangeEvents: vi.fn(),
  repullingTransactions: vi.fn(),
  resetUndecodedTransactionsStatus: vi.fn(),
  setMessage: vi.fn(),
  shouldShowConfirmation: vi.fn(),
  show: vi.fn<(message: unknown, onConfirm: () => void) => void>(),
}));

vi.mock('@/modules/history/events/tx/use-history-transactions', () => ({
  useHistoryTransactions: (): Record<string, unknown> => ({
    repullingEthStakingEvents,
    repullingExchangeEvents,
    repullingTransactions,
  }),
}));

vi.mock('@/modules/history/events/tx/use-repulling-transaction-form', () => ({
  useRepullingTransactionForm: (): Record<string, unknown> => ({
    createDefaultFormData,
    shouldShowConfirmation,
  }),
}));

vi.mock('@/modules/history/use-decoding-status-store', () => ({
  useDecodingStatusStore: (): Record<string, unknown> => ({ resetUndecodedTransactionsStatus }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
  setLevel: vi.fn(),
}));

let scope: ReturnType<typeof effectScope>;

const exchange: Exchange = { location: 'kraken', name: 'Kraken 1' };

function defaultFormData(): RepullingTransactionPayload {
  return { address: '', chain: 'all', fromTimestamp: 100, toTimestamp: 200 };
}

function formHandle(overrides: Partial<RepullingFormHandle> = {}): RepullingFormHandle {
  return {
    getExchangeData: vi.fn<RepullingFormHandle['getExchangeData']>(() => exchange),
    validate: vi.fn<RepullingFormHandle['validate']>(async () => Promise.resolve(true)),
    ...overrides,
  };
}

function submission(
  form: RepullingFormHandle | null = formHandle(),
  callbacks: {
    onExchangeEvents?: (exchanges: Exchange[]) => void;
    onTransactions?: (result: RepullingTransactionResult) => void;
  } = {},
): ReturnType<typeof useRepullingTransactionSubmission> & { open: ReturnType<typeof ref<boolean>> } {
  const open = ref<boolean>(true);
  scope = effectScope();
  const api = scope.run(() => useRepullingTransactionSubmission({ form, open, ...callbacks }))!;
  return { ...api, open };
}

describe('modules/history/events/tx/useRepullingTransactionSubmission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createDefaultFormData.mockImplementation(defaultFormData);
    shouldShowConfirmation.mockReturnValue(false);
    repullingTransactions.mockResolvedValue(undefined);
    repullingExchangeEvents.mockResolvedValue(false);
    repullingEthStakingEvents.mockResolvedValue(false);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('before anything is sent', () => {
    it('should not submit a form that does not validate', async () => {
      const form = formHandle({ validate: vi.fn(async () => Promise.resolve(false)) });
      const { open, submit } = submission(form);

      await submit();

      expect(repullingTransactions).not.toHaveBeenCalled();
      expect(get(open)).toBe(true);
    });

    it('should not submit when there is no form to validate', async () => {
      const { submit } = submission(null);

      await submit();

      expect(repullingTransactions).not.toHaveBeenCalled();
    });

    it('should ask for confirmation before a wide blockchain repull', async () => {
      shouldShowConfirmation.mockReturnValue(true);
      const { submit } = submission();

      await submit();

      expect(show).toHaveBeenCalledOnce();
      expect(repullingTransactions).not.toHaveBeenCalled();
    });

    it('should repull once the confirmation is accepted', async () => {
      shouldShowConfirmation.mockReturnValue(true);
      const { submit } = submission();

      await submit();
      show.mock.calls[0][1]();
      await flushPromises();

      expect(repullingTransactions).toHaveBeenCalledOnce();
    });

    it.each(['exchange', 'eth_staking'] as const)('should never confirm a %s repull', async (type) => {
      shouldShowConfirmation.mockReturnValue(true);
      const { modelAccountType, submit } = submission();
      set(modelAccountType, type);

      await submit();

      expect(show).not.toHaveBeenCalled();
    });
  });

  describe('repulling a chain', () => {
    it('should send the payload without the all-chains sentinel the backend does not know', async () => {
      const { modelFormData, submit } = submission();
      set(modelFormData, { address: '0xabc', chain: 'all', fromTimestamp: 100, toTimestamp: 200 });

      await submit();

      expect(repullingTransactions).toHaveBeenCalledExactlyOnceWith({
        address: '0xabc',
        chain: undefined,
        fromTimestamp: 100,
        toTimestamp: 200,
      });
    });

    it('should send a named chain as it stands', async () => {
      repullingTransactions.mockResolvedValue({ newTransactionsCount: 1 });
      const { modelFormData, submit } = submission();
      set(modelFormData, { address: '0xabc', chain: 'ethereum', fromTimestamp: 100, toTimestamp: 200 });

      await submit();

      expect(repullingTransactions).toHaveBeenCalledWith(expect.objectContaining({ chain: 'ethereum' }));
    });

    it('should clear the undecoded status first, since the repull invalidates it', async () => {
      const { submit } = submission();

      await submit();

      expect(resetUndecodedTransactionsStatus).toHaveBeenCalledOnce();
      expect(resetUndecodedTransactionsStatus.mock.invocationCallOrder[0])
        .toBeLessThan(repullingTransactions.mock.invocationCallOrder[0]);
    });

    it('should hand the caller the result when transactions were found', async () => {
      const onTransactions = vi.fn();
      repullingTransactions.mockResolvedValue({ newTransactionsCount: 3 });
      const { submit } = submission(formHandle(), { onTransactions });

      await submit();

      expect(onTransactions).toHaveBeenCalledExactlyOnceWith({ newTransactionsCount: 3 });
    });

    it('should stay quiet when the repull found nothing', async () => {
      const onTransactions = vi.fn();
      const { submit } = submission(formHandle(), { onTransactions });

      await submit();

      expect(onTransactions).not.toHaveBeenCalled();
    });
  });

  describe('repulling an exchange', () => {
    it('should send the account the form names, with the form timestamps', async () => {
      const { modelAccountType, modelFormData, submit } = submission();
      set(modelAccountType, 'exchange');
      set(modelFormData, { address: '', chain: 'all', fromTimestamp: 500, toTimestamp: 600 });

      await submit();

      expect(repullingExchangeEvents).toHaveBeenCalledExactlyOnceWith({
        fromTimestamp: 500,
        location: 'kraken',
        name: 'Kraken 1',
        toTimestamp: 600,
      });
      expect(repullingTransactions).not.toHaveBeenCalled();
    });

    it('should send empty identifiers when the form has no exchange selected', async () => {
      const form = formHandle({ getExchangeData: vi.fn(() => undefined) });
      const { modelAccountType, submit } = submission(form);
      set(modelAccountType, 'exchange');

      await submit();

      expect(repullingExchangeEvents).toHaveBeenCalledWith(expect.objectContaining({ location: '', name: '' }));
    });

    it('should hand the caller the exchange when new events were found', async () => {
      const onExchangeEvents = vi.fn();
      repullingExchangeEvents.mockResolvedValue(true);
      const { modelAccountType, submit } = submission(formHandle(), { onExchangeEvents });
      set(modelAccountType, 'exchange');

      await submit();

      expect(onExchangeEvents).toHaveBeenCalledExactlyOnceWith([exchange]);
    });

    it('should stay quiet when new events were found but no exchange is known', async () => {
      const onExchangeEvents = vi.fn();
      repullingExchangeEvents.mockResolvedValue(true);
      const form = formHandle({ getExchangeData: vi.fn(() => undefined) });
      const { modelAccountType, submit } = submission(form, { onExchangeEvents });
      set(modelAccountType, 'exchange');

      await submit();

      expect(onExchangeEvents).not.toHaveBeenCalled();
    });
  });

  describe('repulling staking events', () => {
    it('should send the staking payload, which the other two never carry', async () => {
      const { modelAccountType, modelEthStakingData, submit } = submission();
      set(modelAccountType, 'eth_staking');
      const payload = get(modelEthStakingData);

      await submit();

      expect(repullingEthStakingEvents).toHaveBeenCalledExactlyOnceWith(payload);
      expect(repullingTransactions).not.toHaveBeenCalled();
      expect(repullingExchangeEvents).not.toHaveBeenCalled();
    });
  });

  describe('what happens around a submission', () => {
    it('should close the dialog rather than hold it open for a background task', async () => {
      const { open, submit } = submission();

      await submit();

      expect(get(open)).toBe(false);
    });

    it('should reset the form so a reopened dialog is not pre-filled', async () => {
      const { modelAccountType, modelFormData, submit } = submission();
      set(modelAccountType, 'exchange');
      set(modelFormData, { address: '0xabc', chain: 'ethereum', fromTimestamp: 1, toTimestamp: 2 });

      await submit();

      expect(get(modelAccountType)).toBe('blockchain');
      expect(get(modelFormData)).toEqual(defaultFormData());
    });

    it('should stop showing progress once the repull is requested', async () => {
      const { submit, submitting } = submission();

      await submit();

      expect(get(submitting)).toBe(false);
    });
  });

  describe('when the repull is rejected', () => {
    it('should show a plain failure as a message', async () => {
      repullingTransactions.mockRejectedValue(new Error('backend down'));
      const { submit } = submission();

      await submit();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith({ description: 'backend down' });
    });

    it('should keep the form filled in, so the user can correct it', async () => {
      repullingTransactions.mockRejectedValue(new Error('backend down'));
      const { modelFormData, submit } = submission();
      set(modelFormData, { address: '0xabc', chain: 'ethereum', fromTimestamp: 1, toTimestamp: 2 });

      await submit();

      expect(get(modelFormData).address).toBe('0xabc');
    });

    it('should route field errors back into the form and re-validate it', async () => {
      repullingTransactions.mockRejectedValue(
        new ApiValidationError(JSON.stringify({ address: ['not an address'] })),
      );
      const form = formHandle();
      const { modelErrorMessages, submit } = submission(form);

      await submit();

      expect(get(modelErrorMessages)).toEqual({ address: ['not an address'] });
      expect(form.validate).toHaveBeenCalledTimes(2);
      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should stop showing progress', async () => {
      repullingTransactions.mockRejectedValue(new Error('backend down'));
      const { submit, submitting } = submission();

      await submit();

      expect(get(submitting)).toBe(false);
    });
  });
});
