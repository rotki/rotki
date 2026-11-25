import type { UseCostBasisOverlayReturn } from '@/modules/history/cost-basis/use-cost-basis-overlay';
import { inject, type InjectionKey, provide, type Ref } from 'vue';

/**
 * Context shared from the history events view down to the (deeply nested, virtualized) event
 * rows, so a row can render its cost basis cell without prop drilling.
 */
export interface CostBasisOverlayContext {
  enabled: Ref<boolean>;
  overlay: UseCostBasisOverlayReturn;
}

const CostBasisOverlayKey: InjectionKey<CostBasisOverlayContext> = Symbol('cost-basis-overlay');

export function provideCostBasisOverlay(context: CostBasisOverlayContext): void {
  provide(CostBasisOverlayKey, context);
}

export function injectCostBasisOverlay(): CostBasisOverlayContext | null {
  return inject(CostBasisOverlayKey, null);
}
