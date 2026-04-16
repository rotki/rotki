import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';

/**
 * Module-level signal that increments when an internal_tx_fixed websocket
 * message is received. Consumers (e.g., useInternalTxConflicts) can watch
 * this ref to refresh without the handler needing to activate any composable.
 */
const internalTxFixedSignal = ref<number>(0);

export { internalTxFixedSignal };

export function createInternalTxFixedHandler(): StateHandler {
  return createStateHandler(() => {
    set(internalTxFixedSignal, get(internalTxFixedSignal) + 1);
  });
}
