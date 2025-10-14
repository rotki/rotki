import type { EvmSwapEvent, SolanaSwapEvent, SwapSubEventModel } from '@/types/history/events/schemas';

export function toSubEvent(event: EvmSwapEvent | SolanaSwapEvent): Required<SwapSubEventModel> {
  return {
    amount: event.amount.toString(),
    asset: event.asset,
    identifier: event.identifier,
    locationLabel: event.locationLabel ?? '',
    userNotes: event.userNotes ?? '',
  };
}
