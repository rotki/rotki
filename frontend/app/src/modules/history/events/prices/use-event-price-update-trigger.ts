import type { InjectionKey } from 'vue';

export { default as EventAssetPriceUpdateDialog } from './EventAssetPriceUpdateDialog.vue';

export interface EventPriceUpdatePayload {
  asset: string;
  timestamp: number;
}

export interface EventPriceUpdateTrigger {
  open: (payload: EventPriceUpdatePayload) => void;
}

export const EventPriceUpdateKey: InjectionKey<EventPriceUpdateTrigger> = Symbol('event-price-update');

export function provideEventPriceUpdate(trigger: EventPriceUpdateTrigger): void {
  provide(EventPriceUpdateKey, trigger);
}

export function injectEventPriceUpdate(): EventPriceUpdateTrigger | null {
  return inject(EventPriceUpdateKey, null);
}
