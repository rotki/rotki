import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { AddSwapEventPayload, EditSwapEventPayload } from '@/modules/history/events/event-edit-payloads';
import type { useHistoryEvents } from '@/modules/history/events/use-history-events';
import type { PriceIntent, usePriceIntents } from '@/modules/history/management/forms/price-intent';
import { HistoryEventEntryType } from '@rotki/common';
import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { mount, type VueWrapper } from '@vue/test-utils';
import { omit } from 'es-toolkit';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick, ref, type Ref, useModel } from 'vue';
import { z } from 'zod';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';

type HistoryEvents = ReturnType<typeof useHistoryEvents>;

type PriceIntents = ReturnType<typeof usePriceIntents>;

const { addHistoryEvent, editHistoryEvent, runPriceIntents, showErrorMessage } = vi.hoisted(() => ({
  addHistoryEvent: vi.fn<HistoryEvents['addHistoryEvent']>(),
  editHistoryEvent: vi.fn<HistoryEvents['editHistoryEvent']>(),
  runPriceIntents: vi.fn<PriceIntents['runPriceIntents']>(),
  showErrorMessage: vi.fn<(message: string) => void>(),
}));

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: (): Pick<HistoryEvents, 'addHistoryEvent' | 'editHistoryEvent'> => ({
    addHistoryEvent,
    editHistoryEvent,
  }),
}));

vi.mock('@/modules/history/management/forms/price-intent', () => ({
  usePriceIntents: (): PriceIntents => ({ runPriceIntents }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => mockUseNotifications({ showErrorMessage }));

interface FormState {
  amount: string;
  asset: string;
  price?: PriceIntent;
}

const PRICE_FAILED_KEY = 'transactions.events.form.asset_price.failed';

const ethPrice: PriceIntent = {
  fromAsset: 'ETH',
  price: '2000',
  timestampMs: 1742901211000,
  toAsset: 'USD',
};

const schema = z.object({
  amount: z.string().min(1, 'amount_required'),
  asset: z.string(),
});

const toEditPayload = vi.fn((payload: AddSwapEventPayload, identifiers: number[]): EditSwapEventPayload => ({
  ...omit(payload, ['uniqueId']),
  identifiers,
}));

function filledState(): FormState {
  return { amount: '1', asset: 'ETH' };
}

function pricedState(): FormState {
  return { ...filledState(), price: ethPrice };
}

function toPayload(state: FormState): AddSwapEventPayload {
  return {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    location: 'kraken',
    receiveAmount: '2000',
    receiveAsset: 'USD',
    spendAmount: state.amount,
    spendAsset: state.asset,
    timestamp: 1742901211,
    uniqueId: 'unique',
    userNotes: ['', ''],
  };
}

type FormHandle = ReturnType<typeof useHistoryEventForm<FormState, AddSwapEventPayload, EditSwapEventPayload>>;

type SaveStatus = Awaited<ReturnType<HistoryEvents['addHistoryEvent']>>;

interface SaveMode {
  identifiers: number[];
  mode: 'add' | 'edit';
  respond: (status: SaveStatus) => void;
}

interface Host {
  handle: FormHandle;
  wrapper: VueWrapper;
}

interface MountOptions {
  errorMessages?: Ref<Record<string, string[]>>;
  serverErrorPaths?: (errors: ValidationErrors) => ValidationErrors;
}

function mountForm({ errorMessages, serverErrorPaths }: MountOptions = {}): Host {
  let handle!: FormHandle;
  const wrapper = mount(defineComponent({
    emits: ['update:stateUpdated'],
    props: { stateUpdated: { default: false, type: Boolean } },
    setup(props) {
      handle = useHistoryEventForm({
        errorMessages,
        serverErrorPaths,
        initial: (): FormState => ({ amount: '', asset: 'ETH' }),
        priceIntentKeys: ['price'],
        priceIntents: state => (state.price ? [state.price] : []),
        schema,
        stateUpdated: useModel(props, 'stateUpdated'),
        toEditPayload,
        transform: toPayload,
      });
      return (): null => null;
    },
  }));
  return { handle, wrapper };
}

describe('useHistoryEventForm', () => {
  beforeEach(() => {
    addHistoryEvent.mockReset().mockResolvedValue({ success: true });
    editHistoryEvent.mockReset().mockResolvedValue({ success: true });
    runPriceIntents.mockReset().mockResolvedValue({ success: true });
    showErrorMessage.mockReset();
    toEditPayload.mockClear();
  });

  describe('add mode', () => {
    it('should create the event from the transformed state', async () => {
      const { handle } = mountForm();
      handle.seed(filledState());

      await expect(handle.save()).resolves.toBe(true);

      expect(addHistoryEvent).toHaveBeenCalledExactlyOnceWith(toPayload(filledState()));
      expect(editHistoryEvent).not.toHaveBeenCalled();
    });

    it('should reset the form to the create default after a save', async () => {
      const { handle } = mountForm();
      handle.seed(filledState());

      await handle.save();

      expect(handle.form.state.amount).toBe('');
    });

    it('should neither write prices nor save when the state does not validate', async () => {
      const { handle } = mountForm();
      handle.form.state.price = ethPrice;

      await expect(handle.save()).resolves.toBe(false);

      expect(runPriceIntents).not.toHaveBeenCalled();
      expect(addHistoryEvent).not.toHaveBeenCalled();
      expect(handle.form.errors('amount')).toEqual(['amount_required']);
    });
  });

  describe('historic prices', () => {
    it('should write the pending prices before saving the event', async () => {
      const { handle } = mountForm();
      handle.seed(pricedState());

      await handle.save();

      expect(runPriceIntents).toHaveBeenCalledExactlyOnceWith([ethPrice]);
      expect(runPriceIntents.mock.invocationCallOrder[0]).toBeLessThan(addHistoryEvent.mock.invocationCallOrder[0]);
    });

    it.each([
      { case: 'its own message', message: 'price rejected', shown: 'price rejected' },
      { case: 'the generic message when it has none', message: '', shown: PRICE_FAILED_KEY },
    ])('should not save the event when a price write fails, and show $case', async ({ message, shown }) => {
      runPriceIntents.mockResolvedValue({ message, success: false });
      const { handle } = mountForm();
      handle.seed(pricedState());

      await expect(handle.save()).resolves.toBe(false);

      expect(showErrorMessage).toHaveBeenCalledExactlyOnceWith(shown);
      expect(addHistoryEvent).not.toHaveBeenCalled();
    });

    it('should not save an edited event when its price write fails', async () => {
      runPriceIntents.mockResolvedValue({ message: 'price rejected', success: false });
      const { handle } = mountForm();
      handle.seed(filledState(), [7]);
      handle.form.state.amount = '3';
      handle.form.state.price = ethPrice;

      await expect(handle.save()).resolves.toBe(false);

      expect(editHistoryEvent).not.toHaveBeenCalled();
    });
  });

  describe('edit mode', () => {
    it('should send the edit payload built for the seeded identifiers', async () => {
      const { handle } = mountForm();
      handle.seed(filledState(), [7, 8]);
      handle.form.state.amount = '3';

      await expect(handle.save()).resolves.toBe(true);

      expect(toEditPayload).toHaveBeenCalledExactlyOnceWith(toPayload({ ...filledState(), amount: '3' }), [7, 8]);
      expect(editHistoryEvent).toHaveBeenCalledExactlyOnceWith(toEditPayload.mock.results[0]?.value);
      expect(addHistoryEvent).not.toHaveBeenCalled();
    });

    it('should add the next event after an edit was saved', async () => {
      const { handle } = mountForm();
      handle.seed(filledState(), [7]);
      handle.form.state.amount = '3';
      await handle.save();

      handle.form.state.amount = '5';
      await expect(handle.save()).resolves.toBe(true);

      expect(addHistoryEvent).toHaveBeenCalledExactlyOnceWith(toPayload({ ...filledState(), amount: '5' }));
      expect(editHistoryEvent).toHaveBeenCalledOnce();
    });

    it('should write an edited price without re-sending the unchanged event', async () => {
      const { handle } = mountForm();
      handle.seed(filledState(), [7]);
      handle.form.state.price = ethPrice;

      await expect(handle.save()).resolves.toBe(true);

      expect(runPriceIntents).toHaveBeenCalledExactlyOnceWith([ethPrice]);
      expect(editHistoryEvent).not.toHaveBeenCalled();
    });
  });

  describe('server errors', () => {
    const modes: readonly SaveMode[] = [
      { identifiers: [], mode: 'add', respond: status => addHistoryEvent.mockResolvedValue(status) },
      { identifiers: [7], mode: 'edit', respond: status => editHistoryEvent.mockResolvedValue(status) },
    ];

    function seedEdited(handle: FormHandle, identifiers: number[]): void {
      handle.seed(filledState(), identifiers);
      handle.form.state.amount = '3';
    }

    it.each(modes)('should show a plain message as a notification and leave the fields clean ($mode)', async ({ identifiers, respond }) => {
      respond({ message: 'backend said no', success: false });
      const { handle } = mountForm();
      seedEdited(handle, identifiers);

      await expect(handle.save()).resolves.toBe(false);

      expect(showErrorMessage).toHaveBeenCalledExactlyOnceWith('backend said no');
      expect(handle.form.errors('amount')).toEqual([]);
    });

    it.each(modes)('should show a field map on the fields, without a notification ($mode)', async ({ identifiers, respond }) => {
      respond({ message: { amount: ['too small'] }, success: false });
      const { handle } = mountForm();
      seedEdited(handle, identifiers);

      await expect(handle.save()).resolves.toBe(false);

      expect(handle.form.errors('amount')).toEqual(['too small']);
      expect(showErrorMessage).not.toHaveBeenCalled();
    });

    it('should show a field error the endpoint sends as one message, not split into characters', async () => {
      addHistoryEvent.mockResolvedValue({ message: { amount: 'too small' }, success: false });
      const { handle } = mountForm();
      handle.seed(filledState());

      await expect(handle.save()).resolves.toBe(false);

      expect(handle.form.errors('amount')).toEqual(['too small']);
    });

    it('should report a save rejected with an empty message as unsaved, without showing anything', async () => {
      addHistoryEvent.mockResolvedValue({ message: '', success: false });
      const { handle } = mountForm();
      handle.seed(filledState());

      await expect(handle.save()).resolves.toBe(false);

      expect(showErrorMessage).not.toHaveBeenCalled();
      expect(handle.form.errors('amount')).toEqual([]);
      expect(handle.form.state.amount).toBe('1');
    });

    it('should drop the field errors of a failed save when a later save fails with a plain message', async () => {
      addHistoryEvent.mockResolvedValueOnce({ message: { amount: ['too small'] }, success: false });
      addHistoryEvent.mockResolvedValueOnce({ message: 'backend said no', success: false });
      const { handle } = mountForm();
      handle.seed(filledState());

      await handle.save();
      await handle.save();

      expect(handle.form.errors('amount')).toEqual([]);
    });

    it('should mirror errors written by another source into the form', async () => {
      const errorMessages = ref<Record<string, string[]>>({});
      const { handle } = mountForm({ errorMessages });
      handle.seed(filledState());

      set(errorMessages, { amount: ['lookup failed'] });
      await nextTick();

      expect(handle.form.errors('amount')).toEqual(['lookup failed']);
    });

    it('should move the field errors of a rejected save onto the form\'s own paths', async () => {
      addHistoryEvent.mockResolvedValue({ message: { spendAmount: ['too small'] }, success: false });
      const { handle } = mountForm({ serverErrorPaths: errors => ({ amount: errors.spendAmount }) });
      handle.seed(filledState());

      await expect(handle.save()).resolves.toBe(false);

      expect(handle.form.errors('amount')).toEqual(['too small']);
    });

    it('should leave errors written by another source where they are', async () => {
      const errorMessages = ref<Record<string, string[]>>({});
      const { handle } = mountForm({ errorMessages, serverErrorPaths: () => ({}) });
      handle.seed(filledState());

      set(errorMessages, { amount: ['lookup failed'] });
      await nextTick();

      expect(handle.form.errors('amount')).toEqual(['lookup failed']);
    });
  });

  describe('prompt on close', () => {
    it('should flag the dialog once the form is edited and clear it on a save', async () => {
      const { handle, wrapper } = mountForm();
      handle.seed(filledState());

      handle.form.state.amount = '3';
      await nextTick();
      expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);

      await handle.save();
      await nextTick();
      expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([false]);
    });
  });
});
