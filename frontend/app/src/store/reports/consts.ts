import { ComputedRef } from 'vue';
import { ActionDataEntry } from '@/store/types';
import { CostBasisMethod } from '@/types/user';

export const useCostBasisMethod = () => {
  const { tc } = useI18n();
  const costBasisMethodData: ComputedRef<ActionDataEntry<CostBasisMethod>[]> =
    computed(() => [
      {
        identifier: CostBasisMethod.FIFO,
        label: tc('account_settings.cost_basis_method_settings.labels.fifo')
      },
      {
        identifier: CostBasisMethod.LIFO,
        label: tc('account_settings.cost_basis_method_settings.labels.lifo')
      },
      {
        identifier: CostBasisMethod.HIFO,
        label: tc('account_settings.cost_basis_method_settings.labels.hifo')
      },
      {
        identifier: CostBasisMethod.ACB,
        label: tc('account_settings.cost_basis_method_settings.labels.acb')
      }
    ]);

  return {
    costBasisMethodData
  };
};
