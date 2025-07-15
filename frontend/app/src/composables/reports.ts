import type { ComputedRef } from 'vue';
import type { ActionDataEntry } from '@/types/action';
import { CostBasisMethod } from '@/types/user';

type CostBasicRef = ComputedRef<ActionDataEntry<CostBasisMethod>[]>;

export function useCostBasisMethod(): {
  costBasisMethodData: CostBasicRef;
} {
  const { t } = useI18n({ useScope: 'global' });
  const costBasisMethodData: CostBasicRef = computed(() => [
    {
      identifier: CostBasisMethod.FIFO,
      label: t('account_settings.cost_basis_method_settings.labels.fifo'),
    },
    {
      identifier: CostBasisMethod.LIFO,
      label: t('account_settings.cost_basis_method_settings.labels.lifo'),
    },
    {
      identifier: CostBasisMethod.HIFO,
      label: t('account_settings.cost_basis_method_settings.labels.hifo'),
    },
    {
      identifier: CostBasisMethod.ACB,
      label: t('account_settings.cost_basis_method_settings.labels.acb'),
    },
  ]);

  return {
    costBasisMethodData,
  };
}
