import type { MaybeRefOrGetter, Ref } from 'vue';
import { isValidEvmTxHash } from '@rotki/common';
import { err, isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { isActionable, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import {
  type EvmTransactionLookupPayload,
  type EvmTransactionLookupResult,
  EvmTransactionLookupResultSchema,
  useHistoryEventsApi,
} from '@/modules/history/api/events/use-history-events-api';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

export interface EvmTxAutoFillOptions {
  txHash: MaybeRefOrGetter<string>;
  evmChain: MaybeRefOrGetter<string>;
  relatedAddress: MaybeRefOrGetter<string>;
  enabled: MaybeRefOrGetter<boolean>;
  errorMessages: Ref<Record<string, string[]>>;
  /** Form-specific keys to write lookup errors into, so they surface as that field's server errors. */
  errorFields: { txHash: string; relatedAddress: string };
  onResolved: (result: EvmTransactionLookupResult) => void;
  debounce?: number;
}

interface UseEvmTxAutoFillReturn {
  loading: Readonly<Ref<boolean>>;
  canRetry: Readonly<Ref<boolean>>;
  /** True when the tx hash + chain are set but the related address is missing — the user has to pick an account before the lookup can fire. */
  needsRelatedAddress: Readonly<Ref<boolean>>;
  retry: () => Promise<void>;
  reset: () => void;
}

/**
 * The prefix the backend wraps its inner exception in when a transaction cannot be found.
 *
 * @remarks
 * Matched so the user is shown a clean translated message rather than the doubled-up original,
 * which reads `Unable to find transaction 0x… at gnosis: Transaction 0x… was not found on gnosis`.
 */
const NOT_FOUND_PREFIX = 'Unable to find transaction';

export function useEvmTxAutoFill(options: EvmTxAutoFillOptions): UseEvmTxAutoFillReturn {
  const {
    txHash,
    evmChain,
    relatedAddress,
    enabled,
    errorMessages,
    errorFields,
    onResolved,
    debounce = 400,
  } = options;
  const { t } = useI18n({ useScope: 'global' });
  const { lookupEvmTransaction } = useHistoryEventsApi();
  const { cancelByPrefix, submitTask } = useNativeTask();

  const loading = shallowRef<boolean>(false);
  const canRetry = shallowRef<boolean>(false);

  const needsRelatedAddress = computed<boolean>(() =>
    toValue(enabled)
    && isValidEvmTxHash(toValue(txHash))
    && !!toValue(evmChain)
    && !toValue(relatedAddress),
  );

  let currentRequestId = 0;

  function readPayload(): EvmTransactionLookupPayload | null {
    const hash = toValue(txHash);
    const chain = toValue(evmChain);
    const address = toValue(relatedAddress);

    if (!isValidEvmTxHash(hash) || !chain || !address) {
      return null;
    }
    return { evmChain: chain, relatedAddress: address, txHash: hash };
  }

  function writeError(field: string, message: string): void {
    const current = get(errorMessages);
    const existing = current[field] ?? [];
    if (message) {
      set(errorMessages, { ...current, [field]: [message] });
    }
    else if (existing.length > 0) {
      set(errorMessages, { ...current, [field]: [] });
    }
  }

  function applyApiValidationError(err: ApiValidationError): void {
    const fieldErrors = err.getValidationErrors({
      relatedAddress: toValue(relatedAddress),
    });

    if (typeof fieldErrors === 'string') {
      writeError(errorFields.txHash, fieldErrors);
      return;
    }

    const relatedAddressMessages = fieldErrors.relatedAddress;
    const relatedAddressMessage = Array.isArray(relatedAddressMessages)
      ? relatedAddressMessages[0] ?? ''
      : (relatedAddressMessages ?? '');

    if (relatedAddressMessage) {
      writeError(errorFields.relatedAddress, relatedAddressMessage);
    }
  }

  function applyFailure(message: string): void {
    if (message.startsWith(NOT_FOUND_PREFIX)) {
      writeError(
        errorFields.txHash,
        t('actions.evm_tx_lookup.error.not_found', { chain: toValue(evmChain) }),
      );
      // Retrying a confirmed not-found is just noise.
      set(canRetry, false);
      return;
    }
    writeError(errorFields.txHash, message || t('actions.evm_tx_lookup.error.generic'));
    set(canRetry, true);
  }

  async function performLookup(payload: EvmTransactionLookupPayload): Promise<void> {
    const requestId = ++currentRequestId;
    cancelByPrefix(ActivityKind.HISTORY_EVENTS, ActivityPart.LOOKUP);

    set(loading, true);
    set(canRetry, false);
    writeError(errorFields.txHash, '');
    writeError(errorFields.relatedAddress, '');

    const outcome = await submitTask<EvmTransactionLookupResult>({
      id: makeActivityId(ActivityKind.HISTORY_EVENTS, ActivityPart.LOOKUP, requestId, payload.txHash),
      kind: ActivityKind.HISTORY_EVENTS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<EvmTransactionLookupResult, TaskError>> => {
        try {
          return mapResult(
            await runTask<EvmTransactionLookupResult>(
              async () => lookupEvmTransaction(payload),
            ),
            value => value,
          );
        }
        catch (error_: unknown) {
          return err(TaskFailed({ cause: error_, message: getErrorMessage(error_) }));
        }
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.history_events.lookup'), { tx: payload.txHash }),
      title: t('task_center.group.history_events'),
    });

    // Discard stale results — only the latest invocation may touch form state (and own `loading`).
    if (requestId !== currentRequestId) {
      return;
    }

    if (!isErr(outcome)) {
      onResolved(EvmTransactionLookupResultSchema.parse(outcome.value));
    }
    else if (isActionable(outcome.error)) {
      const cause = outcome.error.cause;
      if (cause instanceof ApiValidationError) {
        applyApiValidationError(cause);
      }
      else {
        applyFailure(outcome.error.message);
      }
    }

    set(loading, false);
  }

  function reset(): void {
    // Bump the id so any in-flight result is treated as stale and discarded.
    currentRequestId++;
    set(loading, false);
    set(canRetry, false);
    writeError(errorFields.txHash, '');
    writeError(errorFields.relatedAddress, '');
  }

  async function retry(): Promise<void> {
    const payload = readPayload();
    if (!payload) {
      return;
    }
    await performLookup(payload);
  }

  watchDebounced(
    () => [toValue(enabled), toValue(txHash), toValue(evmChain), toValue(relatedAddress)] as const,
    async ([isEnabled]) => {
      if (!isEnabled) {
        reset();
        return;
      }

      const payload = readPayload();
      if (!payload) {
        reset();
        return;
      }

      await performLookup(payload);
    },
    { debounce },
  );

  return {
    canRetry: readonly(canRetry),
    loading: readonly(loading),
    needsRelatedAddress,
    reset,
    retry,
  };
}
