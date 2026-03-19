import type {
  EvmSwapEvent,
  SolanaSwapEvent,
  StarknetSwapEvent,
  SwapSubEventModel,
} from '@/types/history/events/schemas';

export function toSubEvent(event: EvmSwapEvent | SolanaSwapEvent | StarknetSwapEvent): Required<SwapSubEventModel> {
  return {
    amount: event.amount.toString(),
    asset: event.asset,
    identifier: event.identifier,
    locationLabel: event.locationLabel ?? '',
    userNotes: event.userNotes ?? '',
  };
}

export function getAssetMovementsType(eventSubtype: string): 'deposit' | 'withdrawal' {
  if (eventSubtype === 'receive') {
    return 'deposit';
  }
  return 'withdrawal';
}
