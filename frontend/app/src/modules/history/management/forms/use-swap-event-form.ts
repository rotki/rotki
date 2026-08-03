import type { ModelRef, Ref, UnwrapNestedRefs } from 'vue';
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { AddEvmSwapEventPayload, AddSolanaSwapEventPayload } from '@/modules/history/events/schemas';
import type { SwapSubEventState } from '@/modules/history/management/forms/swap/swap-sub-event';
import { type FormApi, useForm } from '@/modules/core/form/use-form';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import { collectPriceIntents, usePriceIntents } from '@/modules/history/management/forms/price-intent';

type SwapPayload = AddEvmSwapEventPayload | AddSolanaSwapEventPayload;

type SwapFormMessage = ValidationErrors | string;

/** The part of a swap form's state this composable itself reads: the three sub-event lists. */
interface SwapFormState {
  fee: SwapSubEventState[];
  hasFee: boolean;
  receive: SwapSubEventState[];
  spend: SwapSubEventState[];
}

interface UseSwapEventFormOptions<TState extends SwapFormState> {
  /** Create-default or edit seed for the form state. */
  readonly initial: () => TState;
  /** The form's validation schema, whose issue paths address the state. */
  readonly schema: ZodType;
  /** Form state to API payload. */
  readonly transform: (state: UnwrapNestedRefs<TState>) => SwapPayload;
  /** The dialog's `prompt-on-close` flag, kept in step with the form being dirty. */
  readonly stateUpdated: ModelRef<boolean>;
  /**
   * Field errors coming from outside the schema, mirrored into the form as server errors. Passed in
   * only by a form that has another writer, i.e. the EVM one, whose transaction lookup reports its
   * failures through the same channel; otherwise the API's rejection of a save is the only source
   * and the composable owns the ref.
   */
  readonly errorMessages?: Ref<Record<string, string[]>>;
}

interface UseSwapEventFormReturn<TState extends SwapFormState> {
  readonly form: FormApi<TState, SwapPayload, SwapFormMessage>;
  /** Loads an existing group into the form. Without identifiers the form stays in add mode. */
  readonly seed: (state: TState, identifiers?: number[]) => void;
  readonly save: () => Promise<boolean>;
}

/**
 * The shared behaviour of the EVM and Solana swap forms, which differ only in their state shape,
 * schema and payload.
 *
 * The save pipeline is deliberately explicit about its order: validate, then persist the pending
 * historic prices, then decide whether the event itself needs saving at all. Prices run even when
 * the event is unchanged, because editing only a price is a legitimate edit.
 */
export function useSwapEventForm<TState extends SwapFormState>(
  options: UseSwapEventFormOptions<TState>,
): UseSwapEventFormReturn<TState> {
  const { initial, schema, stateUpdated, transform } = options;
  const errorMessages = options.errorMessages ?? ref<Record<string, string[]>>({});

  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage } = useNotifications();
  const { addHistoryEvent, editHistoryEvent } = useHistoryEvents();
  const { runPriceIntents } = usePriceIntents();

  const identifiers = ref<number[]>([]);

  const form = useForm<TState, SwapPayload, SwapFormMessage>({
    initial,
    schema,
    submit: async (payload) => {
      const ids = get(identifiers);
      return ids.length > 0
        ? editHistoryEvent({ ...payload, identifiers: ids })
        : addHistoryEvent(payload);
    },
    transform,
  });

  function seed(state: TState, ids: number[] = []): void {
    form.reset(state);
    set(identifiers, ids);
  }

  async function persistPrices(): Promise<boolean> {
    const { fee, receive, spend } = form.state;
    const status = await runPriceIntents(collectPriceIntents(spend, receive, fee));
    if (status.success)
      return true;

    showErrorMessage(status.message || t('transactions.events.form.asset_price.failed'));
    return false;
  }

  async function save(): Promise<boolean> {
    if (!form.validate())
      return false;

    if (!await persistPrices())
      return false;

    const isEditMode = get(identifiers).length > 0;
    // Nothing about the event changed, so there is nothing to send; any price edit already ran.
    if (isEditMode && !get(form.dirty))
      return true;

    const outcome = await form.submit();

    if (outcome.outcome === 'success') {
      form.reset();
      set(identifiers, []);
      return true;
    }

    if (outcome.outcome === 'error' && outcome.message) {
      const { message } = outcome;
      if (typeof message === 'string')
        showErrorMessage(message);
      set(errorMessages, typeof message === 'string' ? {} : message);
    }

    return false;
  }

  watchImmediate(errorMessages, (errors) => {
    form.setServerErrors(errors);
  });

  watch(form.dirty, (dirty) => {
    set(stateUpdated, dirty);
  });

  onUnmounted(() => {
    set(stateUpdated, false);
  });

  return {
    form,
    save,
    seed,
  };
}
