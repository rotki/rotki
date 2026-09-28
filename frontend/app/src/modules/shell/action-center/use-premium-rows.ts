import type { ComputedRef } from 'vue';
import { externalLinks } from '@shared/external-links';
import { none, some } from 'plainfp/option';
import { type ActionItem, type ActionItemOption, type ActionTarget, ActionUrgency, applicable, createActionItem } from '@/modules/core/action-center/types';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { usePremiumOperations } from '@/modules/premium/use-premium-operations';
import {
  conditionRowId,
  isConditionOf,
  PremiumInactiveCause,
  RaisedConditionKind,
  type RaisedConditionOf,
  useRaisedConditionsStore,
} from '@/modules/shell/action-center/use-raised-conditions-store';

type PremiumInactiveCondition = RaisedConditionOf<typeof RaisedConditionKind.PREMIUM_INACTIVE>;

const isPremiumInactive = isConditionOf(RaisedConditionKind.PREMIUM_INACTIVE);

const PREMIUM_SETTINGS: ActionTarget = { kind: 'route', to: { name: '/api-keys/premium/' } };

const RENEW: ActionTarget = { kind: 'external', url: externalLinks.manageSubscriptions };

/**
 * The premium row: a saved premium key that does not work.
 *
 * @remarks
 * Raised by the backend's hourly premium check, and gone once a check finds the key working, a new
 * key is saved or the key is removed. An unreachable server is rotki's to retry, so that row is only
 * worth a look.
 */
export function usePremiumRows(): ComputedRef<ActionItem[]> {
  const { t } = useI18n({ useScope: 'global' });

  const { conditions } = storeToRefs(useRaisedConditionsStore());
  const { deletePremium } = usePremiumOperations();
  const { show } = useConfirmStore();

  const removeKey: ActionItemOption = {
    danger: true,
    icon: 'lu-trash-2',
    id: 'remove-premium-key',
    label: t('action_center.rows.integrations.premium_inactive.remove_key'),
    target: {
      kind: 'run',
      run: () => show({
        message: t('action_center.rows.integrations.premium_inactive.remove_confirm.message'),
        title: t('action_center.rows.integrations.premium_inactive.remove_confirm.title'),
      }, async () => {
        await deletePremium();
      }),
    },
  };

  function description({ cause, reason }: PremiumInactiveCondition): string {
    switch (cause) {
      case PremiumInactiveCause.EXPIRED:
        return t('action_center.rows.integrations.premium_inactive.description_expired');
      case PremiumInactiveCause.DEVICE_LIMIT:
        return t('action_center.rows.integrations.premium_inactive.description_device_limit', { reason: reason ?? '' });
      case PremiumInactiveCause.UNREACHABLE:
        return t('action_center.rows.integrations.premium_inactive.description_unreachable');
    }
  }

  function row(condition: PremiumInactiveCondition): ActionItem {
    const expired = condition.cause === PremiumInactiveCause.EXPIRED;
    return createActionItem<ActionTarget, string>({
      actionLabel: expired
        ? t('action_center.rows.integrations.premium_inactive.renew')
        : t('action_center.rows.integrations.premium_inactive.settings'),
      checkTarget: PREMIUM_SETTINGS,
      count: 1,
      description: description(condition),
      icon: 'lu-crown',
      id: conditionRowId(condition),
      options: applicable<ActionItemOption>([
        expired
          ? some({ icon: 'lu-settings', id: 'premium-settings', label: t('action_center.rows.integrations.premium_inactive.settings'), target: PREMIUM_SETTINGS })
          : none,
        some(removeKey),
      ]),
      urgency: condition.cause === PremiumInactiveCause.UNREACHABLE ? ActionUrgency.AUTOMATIC : ActionUrgency.DECISION,
      target: expired ? RENEW : PREMIUM_SETTINGS,
      title: t('action_center.rows.integrations.premium_inactive.title'),
    });
  }

  return computed<ActionItem[]>(() => get(conditions).filter(isPremiumInactive).map(row));
}
