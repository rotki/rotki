import type { EvmSwapEvent, SwapSubEventModel } from '@/types/history/events';

export function toSubEvent(event: EvmSwapEvent): Required<SwapSubEventModel> {
  return {
    amount: event.amount.toString(),
    asset: event.asset,
    identifier: event.identifier,
    locationLabel: event.locationLabel ?? '',
    userNotes: event.userNotes ?? '',
  };
}
