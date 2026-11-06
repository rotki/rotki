import type { InjectionKey } from 'vue';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';

/** Shows `question` in the enclosing menu in place of its entries, and calls `onAccept` once accepted. */
type AskInMenu = (question: ConfirmQuestion, onAccept: () => void) => void;

const ConfirmMenuAskKey: InjectionKey<AskInMenu> = Symbol('confirm-menu-ask');

/**
 * Hands a `ConfirmMenu`'s way of asking to every entry inside it.
 *
 * @remarks
 * The menu's default slot also passes `ask` to entries written inline. This covers the entries that
 * are components of their own (a bulk action, the asset database resets), which never see the slot.
 */
export function provideConfirmMenuAsk(ask: AskInMenu): void {
  provide(ConfirmMenuAskKey, ask);
}

/**
 * How an entry asks its question inside the `ConfirmMenu` it sits in.
 *
 * @returns `undefined` outside a `ConfirmMenu`
 */
export function useConfirmMenuAsk(): AskInMenu | undefined {
  return inject(ConfirmMenuAskKey, undefined);
}
