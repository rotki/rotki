import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';

/**
 * What each duplicate group action asks beside its button before it runs on `count` groups.
 *
 * @remarks
 * One group gets the singular wording, which describes what the action does; more get the count.
 */
interface UseDuplicatesQuestionReturn {
  fixQuestion: (count: number) => ConfirmQuestion;
  markNonDuplicatedQuestion: (count: number) => ConfirmQuestion;
  restoreQuestion: (count: number) => ConfirmQuestion;
}

export function useDuplicatesQuestion(): UseDuplicatesQuestionReturn {
  const { t } = useI18n({ useScope: 'global' });

  function fixQuestion(count: number): ConfirmQuestion {
    const confirmLabel = t('customized_event_duplicates.actions.fix');
    return count === 1
      ? { confirmLabel, message: t('customized_event_duplicates.actions.fix_single_confirm'), title: t('customized_event_duplicates.actions.fix_single') }
      : { confirmLabel, message: t('customized_event_duplicates.actions.fix_selected_confirm', { count }), title: t('customized_event_duplicates.actions.fix_selected') };
  }

  function markNonDuplicatedQuestion(count: number): ConfirmQuestion {
    const confirmLabel = t('customized_event_duplicates.actions.mark_non_duplicated');
    return count === 1
      ? { confirmLabel, message: t('customized_event_duplicates.actions.mark_non_duplicated_confirm'), title: confirmLabel }
      : { confirmLabel, message: t('customized_event_duplicates.actions.mark_non_duplicated_selected_confirm', { count }), title: t('customized_event_duplicates.actions.mark_non_duplicated_selected') };
  }

  function restoreQuestion(count: number): ConfirmQuestion {
    const confirmLabel = t('customized_event_duplicates.actions.restore');
    return count === 1
      ? { confirmLabel, message: t('customized_event_duplicates.actions.restore_confirm'), title: confirmLabel }
      : { confirmLabel, message: t('customized_event_duplicates.actions.restore_selected_confirm', { count }), title: t('customized_event_duplicates.actions.restore_selected') };
  }

  return { fixQuestion, markNonDuplicatedQuestion, restoreQuestion };
}
