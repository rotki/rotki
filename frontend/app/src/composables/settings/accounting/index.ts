import { type MaybeRef } from '@vueuse/core';
import {
  type AccountingRuleEntry,
  type AccountingRuleRequestPayload
} from '@/types/settings/accounting';
import { type Collection } from '@/types/collection';

export const useAccountingSettings = () => {
  const { fetchAccountingRules } = useAccountingApi();

  const { t } = useI18n();

  const { notify } = useNotificationsStore();

  const getAccountingRules = async (
    payload: MaybeRef<AccountingRuleRequestPayload>
  ): Promise<Collection<AccountingRuleEntry>> => {
    try {
      const response = await fetchAccountingRules(get(payload));

      return mapCollectionResponse(response);
    } catch (e: any) {
      logger.error(e);
      const message = e?.message ?? e ?? '';

      notify({
        title: t('accounting_settings.rule.fetch_error.title').toString(),
        message: t('accounting_settings.rule.fetch_error.message', {
          message
        }).toString(),
        display: true
      });

      return defaultCollectionState();
    }
  };

  return {
    getAccountingRules
  };
};
