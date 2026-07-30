import type { ComputedRef } from 'vue';
import type { OperatorLabels } from '@/modules/core/table/pill/core/operators';

/**
 * The operator labels the pill and its editors show, translated.
 *
 * The pure core works in operators, not words, so the words are resolved once here and handed to
 * it. Every place an operator is rendered reads from this, so a pill and the editor that produced
 * it cannot disagree about what `is not` is called.
 */
export function useOperatorLabels(): ComputedRef<OperatorLabels> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<OperatorLabels>(() => ({
    after: t('table_filter.operators.after'),
    before: t('table_filter.operators.before'),
    between: t('table_filter.operators.between'),
    gt: t('table_filter.operators.greater_than'),
    is: t('table_filter.operators.is'),
    is_not: t('table_filter.operators.is_not'),
    lt: t('table_filter.operators.less_than'),
  }));
}
