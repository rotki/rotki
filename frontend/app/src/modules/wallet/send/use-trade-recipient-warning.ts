import type { Ref } from 'vue';
import { isValidEthAddress } from '@rotki/common';
import { logger } from '@/modules/core/common/logging/logging';
import { useTradeApi } from '@/modules/wallet/send/use-trade-api';

interface UseTradeRecipientWarningOptions {
  /** The connected address the transaction would be sent from. */
  readonly fromAddress: Readonly<Ref<string | undefined>>;
  /** The recipient as typed, which may not be a well-formed address yet. */
  readonly toAddress: Ref<string>;
}

interface UseTradeRecipientWarningReturn {
  /** Whether to warn that the pair has never transacted before. */
  readonly showNeverInteractedWarning: Readonly<Ref<boolean>>;
}

/**
 * Warns when the connected address has never sent to the recipient before, which is the moment a
 * mistyped address is most likely. The warning is withheld until the recipient parses as an
 * address, and a failed lookup is treated as "no warning" rather than as a false alarm.
 */
export function useTradeRecipientWarning(
  options: UseTradeRecipientWarningOptions,
): UseTradeRecipientWarningReturn {
  const { fromAddress, toAddress } = options;

  const showNeverInteractedWarning = shallowRef<boolean>(false);

  const { getIsInteractedBefore } = useTradeApi();

  watch([fromAddress, toAddress], async ([from, to]) => {
    if (!from || !to || !isValidEthAddress(to)) {
      set(showNeverInteractedWarning, false);
      return;
    }

    try {
      const interacted = await getIsInteractedBefore(from, to);
      set(showNeverInteractedWarning, !interacted);
    }
    catch (error: unknown) {
      set(showNeverInteractedWarning, false);
      logger.error(error);
    }
  });

  return { showNeverInteractedWarning: readonly(showNeverInteractedWarning) };
}
