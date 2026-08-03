import { beforeEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';
import { useForm } from '@/modules/core/form/use-form';

interface SubEvent {
  amount: string;
  asset: string;
}

interface SwapState {
  txRef: string;
  spend: SubEvent[];
}

const SubEventSchema = z.object({
  amount: z.string().min(1, 'amount_required'),
  asset: z.string().min(1, 'asset_required'),
});

const SwapSchema = z.object({
  spend: z.array(SubEventSchema).min(1, 'spend_required'),
  txRef: z.string().min(1, 'tx_required'),
});

function emptyState(): SwapState {
  return {
    spend: [{ amount: '', asset: '' }],
    txRef: '',
  };
}

type SubmitFn = (payload: any) => Promise<{ message?: string; success: boolean }>;

describe('useForm', () => {
  let submitFn: ReturnType<typeof vi.fn<SubmitFn>>;

  function createForm(initial: () => SwapState = emptyState): ReturnType<typeof useForm<SwapState, SwapState>> {
    return useForm<SwapState, SwapState>({
      initial,
      schema: SwapSchema,
      submit: submitFn,
      transform: state => state,
    });
  }

  beforeEach(() => {
    submitFn = vi.fn<SubmitFn>().mockResolvedValue({ success: true });
  });

  describe('validation', () => {
    it('should hide errors until a field is touched', () => {
      const form = createForm();

      expect(form.errors('txRef')).toEqual([]);

      form.touch('txRef');

      expect(form.errors('txRef')).toEqual(['tx_required']);
    });

    it('should key errors by dotted path so rows do not share messages', () => {
      const form = createForm(() => ({
        spend: [{ amount: '1', asset: 'ETH' }, { amount: '', asset: '' }],
        txRef: '0xabc',
      }));

      form.touch('spend.0.amount');
      form.touch('spend.1.amount');

      expect(form.errors('spend.0.amount')).toEqual([]);
      expect(form.errors('spend.1.amount')).toEqual(['amount_required']);
    });

    it('should report valid only when the whole schema parses', () => {
      const form = createForm();

      expect(get(form.valid)).toBe(false);

      form.state.txRef = '0xabc';
      form.state.spend[0].amount = '1';
      form.state.spend[0].asset = 'ETH';

      expect(get(form.valid)).toBe(true);
    });
  });

  describe('touched tracking across row removal', () => {
    it('should keep touched state with the row when an earlier row is removed', () => {
      const form = createForm(() => ({
        spend: [{ amount: '1', asset: 'ETH' }, { amount: '', asset: '' }],
        txRef: '0xabc',
      }));

      // The user blurs the second row's amount, leaving it empty and invalid.
      form.touch('spend.1.amount');
      expect(form.errors('spend.1.amount')).toEqual(['amount_required']);

      // Removing the first row shifts the second into index 0. Its touched flag has to travel with
      // it: keyed by index it would stay on the now-removed row and decorate the wrong one.
      form.state.spend.splice(0, 1);

      expect(form.errors('spend.0.amount')).toEqual(['amount_required']);
    });

    it('should not mark an untouched row as touched when rows shift', () => {
      const form = createForm(() => ({
        spend: [{ amount: '', asset: '' }, { amount: '', asset: '' }],
        txRef: '0xabc',
      }));

      form.touch('spend.0.amount');
      form.state.spend.splice(0, 1);

      // The surviving row was never touched, so it stays quiet.
      expect(form.errors('spend.0.amount')).toEqual([]);
    });
  });

  describe('errorCount', () => {
    it('should count only fields whose errors are visible', () => {
      const form = createForm();

      expect(get(form.errorCount)).toBe(0);

      form.touch('txRef');
      expect(get(form.errorCount)).toBe(1);

      form.touch('spend.0.amount');
      form.touch('spend.0.asset');
      expect(get(form.errorCount)).toBe(3);
    });

    it('should count every invalid field after a submit attempt', async () => {
      const form = createForm();

      await form.submit();

      expect(get(form.errorCount)).toBe(3);
      expect(submitFn).not.toHaveBeenCalled();
    });
  });

  describe('validate', () => {
    it('should reveal every error without submitting', () => {
      const form = createForm();

      expect(form.validate()).toBe(false);
      expect(form.errors('txRef')).toEqual(['tx_required']);
      expect(form.errors('spend.0.amount')).toEqual(['amount_required']);
      expect(submitFn).not.toHaveBeenCalled();
    });

    it('should report a parsing state as valid', () => {
      const form = createForm(() => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }));

      expect(form.validate()).toBe(true);
      expect(submitFn).not.toHaveBeenCalled();
    });
  });

  describe('dirty', () => {
    it('should be false before any edit and true after one', () => {
      const form = createForm();

      expect(get(form.dirty)).toBe(false);

      form.state.txRef = '0xabc';

      expect(get(form.dirty)).toBe(true);
    });

    it('should be false again once the value returns to the seeded one', () => {
      const form = createForm();

      form.state.txRef = '0xabc';
      form.state.txRef = '';

      expect(get(form.dirty)).toBe(false);
    });

    it('should ignore a transient key at any depth', () => {
      const form = useForm<SwapState, SwapState>({
        initial: emptyState,
        schema: SwapSchema,
        submit: submitFn,
        transform: state => state,
        transientKeys: ['draftPrice'],
      });

      Reflect.set(form.state, 'draftPrice', '2000');
      Reflect.set(form.state.spend[0], 'draftPrice', '3000');

      expect(get(form.dirty)).toBe(false);

      form.state.txRef = '0xabc';

      expect(get(form.dirty)).toBe(true);
    });

    it('should reset dirty after a successful submit', async () => {
      const form = createForm(() => ({
        spend: [{ amount: '1', asset: 'ETH' }],
        txRef: '0xabc',
      }));

      form.state.txRef = '0xdef';
      expect(get(form.dirty)).toBe(true);

      await form.submit();

      expect(get(form.dirty)).toBe(false);
    });
  });

  describe('submit', () => {
    it('should not call the injected submit when the state is invalid', async () => {
      const form = createForm();

      const outcome = await form.submit();

      expect(outcome).toEqual({ outcome: 'invalid' });
      expect(submitFn).not.toHaveBeenCalled();
    });

    it('should transform the state into the payload it submits', async () => {
      const transform = vi.fn<(state: SwapState) => { transformed: boolean }>().mockReturnValue({ transformed: true });
      const form = useForm<SwapState, { transformed: boolean }>({
        initial: () => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }),
        schema: SwapSchema,
        submit: submitFn,
        transform,
      });

      const outcome = await form.submit();

      expect(transform).toHaveBeenCalledOnce();
      expect(submitFn).toHaveBeenCalledWith({ transformed: true });
      expect(outcome).toEqual({ outcome: 'success', payload: { transformed: true } });
    });

    it('should surface a failed submit without throwing', async () => {
      submitFn.mockResolvedValue({ message: 'nope', success: false });
      const form = createForm(() => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }));

      const outcome = await form.submit();

      expect(outcome).toEqual({ message: 'nope', outcome: 'error' });
    });

    it('should report submitting while the injected submit is in flight', async () => {
      let release: () => void = () => {};
      submitFn.mockImplementation(async () => new Promise((resolve) => {
        release = (): void => resolve({ success: true });
      }));
      const form = createForm(() => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }));

      const pending = form.submit();
      expect(get(form.submitting)).toBe(true);

      release();
      await pending;

      expect(get(form.submitting)).toBe(false);
    });

    it('should clear submitting when the injected submit rejects', async () => {
      submitFn.mockRejectedValue(new Error('boom'));
      const form = createForm(() => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }));

      await expect(form.submit()).rejects.toThrow('boom');

      expect(get(form.submitting)).toBe(false);
    });
  });

  describe('server errors', () => {
    it('should show a server error immediately, without needing a touch', () => {
      const form = createForm(() => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }));

      form.setServerErrors({ txRef: ['already known'] });

      expect(form.errors('txRef')).toEqual(['already known']);
    });

    it('should drop a server error once the user edits that field', () => {
      const form = createForm(() => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }));

      form.setServerErrors({ txRef: ['already known'] });
      form.state.txRef = '0xdef';

      expect(form.errors('txRef')).toEqual([]);
    });

    it('should keep a server error on a field the user has not edited', () => {
      const form = createForm(() => ({ spend: [{ amount: '1', asset: 'ETH' }], txRef: '0xabc' }));

      form.setServerErrors({ 'spend.0.amount': ['too small'], 'txRef': ['already known'] });
      form.state.txRef = '0xdef';

      expect(form.errors('txRef')).toEqual([]);
      expect(form.errors('spend.0.amount')).toEqual(['too small']);
    });

    it('should address server errors on rows by path', () => {
      const form = createForm(() => ({
        spend: [{ amount: '1', asset: 'ETH' }, { amount: '2', asset: 'BTC' }],
        txRef: '0xabc',
      }));

      form.setServerErrors({ 'spend.1.amount': ['too small'] });

      expect(form.errors('spend.0.amount')).toEqual([]);
      expect(form.errors('spend.1.amount')).toEqual(['too small']);
    });
  });

  describe('reset', () => {
    it('should restore the seed and clear touched, server errors and dirty', () => {
      const form = createForm();

      form.state.txRef = '0xabc';
      form.touch('txRef');
      form.setServerErrors({ txRef: ['already known'] });

      form.reset();

      expect(form.state.txRef).toBe('');
      expect(form.errors('txRef')).toEqual([]);
      expect(get(form.dirty)).toBe(false);
    });

    it('should seed from the given state when one is passed', () => {
      const form = createForm();

      form.reset({ spend: [{ amount: '5', asset: 'BTC' }], txRef: '0xseeded' });

      expect(form.state.txRef).toBe('0xseeded');
      expect(form.state.spend).toEqual([{ amount: '5', asset: 'BTC' }]);
      expect(get(form.dirty)).toBe(false);
    });

    it('should keep the state object identity so template bindings survive', () => {
      const form = createForm();
      const before = form.state;

      form.reset({ spend: [{ amount: '5', asset: 'BTC' }], txRef: '0xseeded' });

      expect(form.state).toBe(before);
    });
  });
});
