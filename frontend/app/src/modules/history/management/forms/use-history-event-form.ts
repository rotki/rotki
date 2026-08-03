import type { ModelRef, Ref, UnwrapNestedRefs } from 'vue';
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { AddHistoryEventPayload, ModifyHistoryEventPayload } from '@/modules/history/events/schemas';
import { type FormApi, useForm } from '@/modules/core/form/use-form';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import { type PriceIntent, usePriceIntents } from '@/modules/history/management/forms/price-intent';

type FormMessage = ValidationErrors | string;

interface UseHistoryEventFormOptions<TState extends object, TAdd, TEdit> {
  /** Create-default or edit seed for the form state. */
  readonly initial: () => TState;
  /** The form's validation schema, whose issue paths address the state. */
  readonly schema: ZodType;
  /** Form state to the payload that creates the event. */
  readonly transform: (state: UnwrapNestedRefs<TState>) => TAdd;
  /**
   * The same payload, addressed at the events being edited. Not always a spread: the swap endpoint
   * takes a `uniqueId` when creating and rejects it when editing.
   */
  readonly toEditPayload: (payload: TAdd, identifiers: number[]) => TEdit;
  /** The historic prices to write before saving. Where they sit in the state is form specific. */
  readonly priceIntents?: (state: UnwrapNestedRefs<TState>) => PriceIntent[];
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

interface UseHistoryEventFormReturn<TState extends object, TAdd> {
  readonly form: FormApi<TState, TAdd, FormMessage>;
  /** Loads an existing group into the form. Without identifiers the form stays in add mode. */
  readonly seed: (state: TState, identifiers?: number[]) => void;
  readonly save: () => Promise<boolean>;
}

/**
 * The save pipeline every migrated history event form is driven through.
 *
 * Its order is deliberate: validate, then persist the pending historic prices, then decide whether
 * the event itself needs saving at all. Prices run even when the event is unchanged, because
 * editing only a price is a legitimate edit.
 */
export function useHistoryEventForm<
  TState extends object,
  TAdd extends AddHistoryEventPayload,
  TEdit extends ModifyHistoryEventPayload,
>(
  options: UseHistoryEventFormOptions<TState, TAdd, TEdit>,
): UseHistoryEventFormReturn<TState, TAdd> {
  const { initial, priceIntents, schema, stateUpdated, toEditPayload, transform } = options;
  const errorMessages = options.errorMessages ?? ref<Record<string, string[]>>({});

  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage } = useNotifications();
  const { addHistoryEvent, editHistoryEvent } = useHistoryEvents();
  const { runPriceIntents } = usePriceIntents();

  const identifiers = ref<number[]>([]);

  const form = useForm<TState, TAdd, FormMessage>({
    initial,
    schema,
    submit: async (payload) => {
      const ids = get(identifiers);
      return ids.length > 0
        ? editHistoryEvent(toEditPayload(payload, ids))
        : addHistoryEvent(payload);
    },
    transform,
  });

  function seed(state: TState, ids: number[] = []): void {
    form.reset(state);
    set(identifiers, ids);
  }

  async function persistPrices(): Promise<boolean> {
    if (!priceIntents)
      return true;

    const status = await runPriceIntents(priceIntents(form.state));
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
