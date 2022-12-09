import { type ComputedRef } from 'vue';
import { type ActionDataEntry } from '@/store/types';
import { CostBasisMethod } from '@/types/user';

type CostBasicRef = ComputedRef<ActionDataEntry<CostBasisMethod>[]>;

export const useCostBasisMethod = (): {
  costBasisMethodData: CostBasicRef;
} => {
  const { tc } = useI18n();
  const costBasisMethodData: CostBasicRef = computed(() => [
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
