import { LedgerActionType } from '@/types/history/ledger-action/ledger-actions-type';

export const useLedgerActionData = createSharedComposable(() => {
  const { tc } = useI18n();
  const ledgerActionsData = computed(() => [
    {
      identifier: LedgerActionType.ACTION_INCOME,
      label: tc('ledger_actions.actions.income')
    },
    {
      identifier: LedgerActionType.ACTION_LOSS,
      label: tc('ledger_actions.actions.loss')
    },
    {
      identifier: LedgerActionType.ACTION_DONATION,
      label: tc('ledger_actions.actions.donation')
    },
    {
      identifier: LedgerActionType.ACTION_EXPENSE,
      label: tc('ledger_actions.actions.expense')
    },
    {
      identifier: LedgerActionType.ACTION_DIVIDENDS,
      label: tc('ledger_actions.actions.dividends')
    },
    {
      identifier: LedgerActionType.ACTION_AIRDROP,
      label: tc('ledger_actions.actions.airdrop')
    },
    {
      identifier: LedgerActionType.ACTION_GIFT,
      label: tc('ledger_actions.actions.gift')
    },
    {
      identifier: LedgerActionType.ACTION_GRANT,
      label: tc('ledger_actions.actions.grant')
    }
  ]);
  return {
    ledgerActionsData
  };
});
