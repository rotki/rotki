import { type ComputedRef, hasInjectionContext, type InjectionKey } from 'vue';

/** Which balances a page shows: queried from chains, exchanges and banks, or derived from history. */
export const BalanceView = {
  HISTORY: 'history',
  QUERIED: 'queried',
} as const;

export type BalanceView = (typeof BalanceView)[keyof typeof BalanceView];

/** The route query key a page keeps its view in, so the view is visible and shareable in the URL. */
export const BALANCE_VIEW_QUERY = 'view';

const historyViewKey: InjectionKey<ComputedRef<boolean>> = Symbol('balance-history-view');

/**
 * Makes the history view available to the components a page renders.
 *
 * @remarks
 * Only a page that offers the switch calls this. Shared components read it through
 * {@link useIsHistoryView}, so the same component on a page that never opted in keeps showing
 * queried balances.
 */
export function provideHistoryView(isHistory: ComputedRef<boolean>): void {
  provide(historyViewKey, isHistory);
}

/**
 * Whether the enclosing page shows history-derived balances.
 *
 * @remarks
 * False outside a page that opted in, including when called outside any component.
 */
export function useIsHistoryView(): ComputedRef<boolean> {
  const provided = hasInjectionContext() ? inject(historyViewKey, undefined) : undefined;
  return provided ?? computed<boolean>(() => false);
}
