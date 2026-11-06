import type { MaybeRefOrGetter, Ref } from 'vue';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { RepullingEthStakingPayload, RepullingExchangeEventsPayload, RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import type { AccountType } from '@/modules/history/events/tx/RepullingTransactionForm.vue';
import dayjs from 'dayjs';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { type RepullingTransactionResult, useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import { useRepullingTransactionForm } from '@/modules/history/events/tx/use-repulling-transaction-form';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';

/**
 * The part of `RepullingTransactionForm` this composable drives, kept structural so the submission
 * flow can be tested without mounting the form.
 */
export interface RepullingFormHandle {
  getExchangeData: () => Exchange | undefined;
  validate: () => Promise<boolean>;
}

interface UseRepullingTransactionSubmissionOptions {
  /** The form whose validation gates the submission. */
  form: MaybeRefOrGetter<RepullingFormHandle | null | undefined>;
  /** Whether the dialog is showing; closed as soon as a submission is under way. */
  open: Ref<boolean>;
  /** Called with the exchange that turned out to have new events. */
  onExchangeEvents?: (exchanges: Exchange[]) => void;
  /** Called with the repull result when new transactions were found. */
  onTransactions?: (result: RepullingTransactionResult) => void;
}

interface UseRepullingTransactionSubmissionReturn {
  /** Asking, in the dialog, whether to go ahead with a wide repull that may take a while. */
  askingWideRepull: Readonly<Ref<boolean>>;
  /** Answers the wide-repull question: `true` submits, `false` goes back to the form. */
  answerWideRepull: (proceed: boolean) => Promise<void>;
  /** Which of the three repull kinds the form is on. */
  modelAccountType: Ref<AccountType>;
  /** Per-field backend validation errors, fed back into the form. */
  modelErrorMessages: Ref<ValidationErrors>;
  /** The eth staking form's own payload, which shares no fields with the other two. */
  modelEthStakingData: Ref<RepullingEthStakingPayload>;
  /** The blockchain and exchange payload. */
  modelFormData: Ref<RepullingTransactionPayload>;
  /**
   * Validates, then submits, or asks first when the repull is a wide one.
   *
   * @remarks
   * Only a blockchain repull is ever asked about; an exchange or staking repull is bounded by the
   * account it names. The question is {@link UseRepullingTransactionSubmissionReturn.askingWideRepull},
   * shown in the dialog; the submission waits for its answer.
   */
  submit: () => Promise<void>;
  /** True while a repull is being requested. */
  submitting: Readonly<Ref<boolean>>;
}

function createDefaultEthStakingData(): RepullingEthStakingPayload {
  return {
    entryType: OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
    fromTimestamp: dayjs().subtract(1, 'year').unix(),
    toTimestamp: dayjs().unix(),
  };
}

/**
 * Drives the repulling dialog: which kind of repull the form is on, and submitting it.
 *
 * @remarks
 * The dialog closes the moment a submission starts rather than when it finishes, because a repull
 * runs as a background task and there is nothing further to watch in the dialog.
 *
 * @returns the form's bindings; only {@link UseRepullingTransactionSubmissionReturn.submit} calls
 * the backend
 */
export function useRepullingTransactionSubmission(
  options: UseRepullingTransactionSubmissionOptions,
): UseRepullingTransactionSubmissionReturn {
  const { form, onExchangeEvents, onTransactions, open } = options;

  const submitting = shallowRef<boolean>(false);
  const askingWideRepull = shallowRef<boolean>(false);
  const modelAccountType = shallowRef<AccountType>('blockchain');
  const modelErrorMessages = ref<ValidationErrors>({});

  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { repullingEthStakingEvents, repullingExchangeEvents, repullingTransactions } = useHistoryTransactions();
  const { createDefaultFormData, shouldShowConfirmation } = useRepullingTransactionForm();
  const { resetUndecodedTransactionsStatus } = useDecodingStatusStore();

  const modelFormData = ref<RepullingTransactionPayload>(createDefaultFormData());
  const modelEthStakingData = ref<RepullingEthStakingPayload>(createDefaultEthStakingData());

  function resetForm(): void {
    set(modelFormData, createDefaultFormData());
    set(modelEthStakingData, createDefaultEthStakingData());
    set(modelAccountType, 'blockchain');
  }

  /**
   * Reports a submission that threw.
   *
   * @remarks
   * The dialog closed when the submission started, so a plain failure goes to a toast. Field errors
   * go to the form, which shows them when the dialog is opened again with what was typed.
   */
  async function handleSubmissionError(error: unknown, data: RepullingTransactionPayload): Promise<void> {
    let message: string | ValidationErrors = getErrorMessage(error);

    if (error instanceof ApiValidationError)
      message = error.getValidationErrors(data);

    if (typeof message === 'string') {
      notifyError(t('actions.repulling_transaction.task.title'), message);
    }
    else {
      set(modelErrorMessages, message);
      await toValue(form)?.validate();
    }
  }

  async function handleExchangeSubmission(data: RepullingTransactionPayload): Promise<void> {
    const exchange = toValue(form)?.getExchangeData();
    const exchangePayload: RepullingExchangeEventsPayload = {
      fromTimestamp: data.fromTimestamp,
      identifier: exchange?.identifier ?? '',
      label: exchange ? `${exchange.name} (${exchange.location})` : '',
      toTimestamp: data.toTimestamp,
    };

    const newEventsDetected = await repullingExchangeEvents(exchangePayload);
    if (newEventsDetected && exchange) {
      onExchangeEvents?.([exchange]);
      logger.debug('New exchange events detected');
    }
  }

  async function handleBlockchainSubmission(data: RepullingTransactionPayload): Promise<void> {
    const chain = data.chain === 'all' ? undefined : data.chain;
    const blockchainPayload: RepullingTransactionPayload = {
      address: data.address,
      chain,
      fromTimestamp: data.fromTimestamp,
      toTimestamp: data.toTimestamp,
    };

    resetUndecodedTransactionsStatus();
    const result = await repullingTransactions(blockchainPayload);
    if (result) {
      onTransactions?.(result);
      logger.debug(`New transactions detected${chain ? ` for chain ${chain}` : ' for all chains'}`);
    }
  }

  async function performSubmission(): Promise<void> {
    const data = get(modelFormData);
    const type = get(modelAccountType);

    try {
      set(submitting, true);
      set(open, false);

      if (type === 'exchange')
        await handleExchangeSubmission(data);
      else if (type === 'eth_staking')
        await repullingEthStakingEvents(get(modelEthStakingData));
      else
        await handleBlockchainSubmission(data);

      resetForm();
    }
    catch (error: unknown) {
      await handleSubmissionError(error, data);
    }
    finally {
      set(submitting, false);
    }
  }

  async function submit(): Promise<void> {
    const valid = await toValue(form)?.validate();
    if (!valid)
      return;

    if (get(modelAccountType) === 'blockchain' && shouldShowConfirmation(get(modelFormData)))
      set(askingWideRepull, true);
    else
      await performSubmission();
  }

  async function answerWideRepull(proceed: boolean): Promise<void> {
    set(askingWideRepull, false);
    if (proceed)
      await performSubmission();
  }

  watch(open, (shown) => {
    if (!shown)
      set(askingWideRepull, false);
  });

  return {
    answerWideRepull,
    askingWideRepull: readonly(askingWideRepull),
    modelAccountType,
    modelErrorMessages,
    modelEthStakingData,
    modelFormData,
    submit,
    submitting: readonly(submitting),
  };
}
