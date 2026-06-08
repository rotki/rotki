import type { InjectionKey, Ref } from 'vue';
import type { UseAccountingOverlayReturn } from '@/modules/history/balances/use-accounting-overlay';

/**
 * Context shared from the history events view down to the (deeply nested, virtualized)
 * event rows, so a row can render its balance-at-event cell without prop drilling.
 */
export interface AccountingOverlayContext {
  enabled: Ref<boolean>;
  overlay: UseAccountingOverlayReturn;
}

const AccountingOverlayKey: InjectionKey<AccountingOverlayContext> = Symbol('accounting-overlay');

export function provideAccountingOverlay(context: AccountingOverlayContext): void {
  provide(AccountingOverlayKey, context);
}

export function injectAccountingOverlay(): AccountingOverlayContext | null {
  return inject(AccountingOverlayKey, null);
}
