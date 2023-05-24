import { LedgerActionType } from '@/types/history/ledger-action/ledger-actions-type';

export const useLedgerActionData = createSharedComposable(() => {
  const { t } = useI18n();
  const ledgerActionsData = computed(() => [
    {
      identifier: LedgerActionType.ACTION_INCOME,
      label: t('ledger_actions.actions.income')
    },
    {
      identifier: LedgerActionType.ACTION_LOSS,
      label: t('ledger_actions.actions.loss')
    },
    {
      identifier: LedgerActionType.ACTION_DONATION,
      label: t('ledger_actions.actions.donation')
    },
    {
      identifier: LedgerActionType.ACTION_EXPENSE,
      label: t('ledger_actions.actions.expense')
    },
    {
      identifier: LedgerActionType.ACTION_DIVIDENDS,
      label: t('ledger_actions.actions.dividends')
    },
    {
      identifier: LedgerActionType.ACTION_AIRDROP,
      label: t('ledger_actions.actions.airdrop')
    },
    {
      identifier: LedgerActionType.ACTION_GIFT,
      label: t('ledger_actions.actions.gift')
    },
    {
      identifier: LedgerActionType.ACTION_GRANT,
      label: t('ledger_actions.actions.grant')
    }
  ]);
  return {
    ledgerActionsData
  };
});
