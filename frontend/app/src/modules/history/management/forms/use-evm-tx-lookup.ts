import type { MaybeRefOrGetter, Ref } from 'vue';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { isValidEvmTxHash } from '@rotki/common';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import {
  type EvmTransactionLookupPayload,
  type EvmTransactionLookupResult,
  EvmTransactionLookupResultSchema,
  useHistoryEventsApi,
} from '@/modules/history/api/events/use-history-events-api';

export interface EvmTxAutoFillOptions {
  txHash: MaybeRefOrGetter<string>;
  evmChain: MaybeRefOrGetter<string>;
  relatedAddress: MaybeRefOrGetter<string>;
  enabled: MaybeRefOrGetter<boolean>;
  errorMessages: Ref<Record<string, string[]>>;
  /** Form-specific keys to write lookup errors into (so they flow through vuelidate `$externalResults`). */
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

// Backend wraps the inner exception inside this prefix; matching it lets us
// render a clean translated message instead of e.g.
// `Unable to find transaction 0x… at gnosis: Transaction 0x… was not found on gnosis`.
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
  const { cancelTaskByTaskType, runTask } = useTaskHandler();

  const loading = shallowRef<boolean>(false);
  const canRetry = shallowRef<boolean>(false);

  const needsRelatedAddress = computed<boolean>(() =>
    toValue(enabled)
    && isValidEvmTxHash(toValue(txHash))
    && !!toValue(evmChain)
    && !toValue(relatedAddress),
  );

  // Monotonic id used to discard results from superseded in-flight lookups.
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
    // Only write when there's a real message; preserve other keys.
    if (message) {
      set(errorMessages, { ...current, [field]: [message] });
    }
    else if (existing.length > 0) {
      // Clear only when we previously set something there.
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
    // Cancel any in-flight lookup so the backend stops working on a stale hash.
    await cancelTaskByTaskType(TaskType.LOOKUP_EVM_TRANSACTION);

    set(loading, true);
    set(canRetry, false);
    writeError(errorFields.txHash, '');
    writeError(errorFields.relatedAddress, '');

    try {
      const outcome = await runTask<EvmTransactionLookupResult, TaskMeta>(
        async () => lookupEvmTransaction(payload),
        {
          guard: false,
          meta: { title: t('actions.evm_tx_lookup.title') },
          type: TaskType.LOOKUP_EVM_TRANSACTION,
          unique: false,
        },
      );

      // Discard stale results — only the latest invocation may touch form state.
      if (requestId !== currentRequestId) {
        return;
      }

      if (outcome.success) {
        onResolved(EvmTransactionLookupResultSchema.parse(outcome.result));
        return;
      }

      if (isActionableFailure(outcome)) {
        applyFailure(outcome.message);
      }
    }
    catch (error_: unknown) {
      if (requestId !== currentRequestId) {
        return;
      }

      if (error_ instanceof ApiValidationError) {
        applyApiValidationError(error_);
        return;
      }

      applyFailure(getErrorMessage(error_));
    }
    finally {
      if (requestId === currentRequestId) {
        set(loading, false);
      }
    }
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
