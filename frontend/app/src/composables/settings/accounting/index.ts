import { type MaybeRef } from '@vueuse/core';
import {
  type AccountingRuleConflict,
  type AccountingRuleConflictRequestPayload,
  type AccountingRuleConflictResolution,
  type AccountingRuleEntry,
  type AccountingRuleRequestPayload
} from '@/types/settings/accounting';
import { type Collection } from '@/types/collection';
import { type ActionStatus } from '@/types/action';

export const useAccountingSettings = () => {
  const {
    fetchAccountingRule,
    fetchAccountingRules,
    fetchAccountingRuleConflicts,
    resolveAccountingRuleConflicts: resolveAccountingRuleConflictsCaller
  } = useAccountingApi();

  const { t } = useI18n();

  const { notify } = useNotificationsStore();

  const getAccountingRule = async (
    payload: MaybeRef<AccountingRuleRequestPayload>
  ): Promise<AccountingRuleEntry | null> => {
    try {
      return await fetchAccountingRule(get(payload));
    } catch (e: any) {
      logger.error(e);
      const message = e?.message ?? e ?? '';

      notify({
        title: t('accounting_settings.rule.fetch_error.title'),
        message: t('accounting_settings.rule.fetch_error.message', {
          message
        }),
        display: true
      });

      return null;
    }
  };

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
        title: t('accounting_settings.rule.fetch_error.title'),
        message: t('accounting_settings.rule.fetch_error.message', {
          message
        }),
        display: true
      });

      return defaultCollectionState();
    }
  };

  const getAccountingRulesConflicts = async (
    payload: MaybeRef<AccountingRuleConflictRequestPayload>
  ): Promise<Collection<AccountingRuleConflict>> => {
    try {
      const response = await fetchAccountingRuleConflicts(get(payload));

      return mapCollectionResponse(response);
    } catch (e: any) {
      logger.error(e);
      const message = e?.message ?? e ?? '';

      notify({
        title: t('accounting_settings.rule.conflicts.fetch_error.title'),
        message: t('accounting_settings.rule.conflicts.fetch_error.message', {
          message
        }),
        display: true
      });

      return defaultCollectionState();
    }
  };

  const resolveAccountingRuleConflicts = async (
    payload: AccountingRuleConflictResolution
  ): Promise<ActionStatus> => {
    try {
      await resolveAccountingRuleConflictsCaller(payload);

      return { success: true };
    } catch (e: any) {
      logger.error(e);
      return { success: false, message: e.message };
    }
  };

  return {
    getAccountingRule,
    getAccountingRules,
    getAccountingRulesConflicts,
    resolveAccountingRuleConflicts
  };
};
