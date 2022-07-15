import i18n from '@/i18n';
import { ActionDataEntry } from '@/store/types';
import { CostBasisMethod } from '@/types/user';

export const costBasisMethodData: ActionDataEntry<CostBasisMethod>[] = [
  {
    identifier: CostBasisMethod.Fifo,
    label: i18n
      .t('account_settings.cost_basis_method_settings.labels.fifo')
      .toString()
  },
  {
    identifier: CostBasisMethod.Lifo,
    label: i18n
      .t('account_settings.cost_basis_method_settings.labels.lifo')
      .toString()
  }
];
