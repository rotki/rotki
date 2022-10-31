import { ComputedRef } from 'vue';
import { ActionDataEntry } from '@/store/types';
import { CostBasisMethod } from '@/types/user';

export const useCostBasisMethod = () => {
  const { tc } = useI18n();
  const costBasisMethodData: ComputedRef<ActionDataEntry<CostBasisMethod>[]> =
    computed(() => [
      {
        identifier: CostBasisMethod.Fifo,
        label: tc('account_settings.cost_basis_method_settings.labels.fifo')
      },
      {
        identifier: CostBasisMethod.Lifo,
        label: tc('account_settings.cost_basis_method_settings.labels.lifo')
      }
    ]);

  return {
    costBasisMethodData
  };
};
