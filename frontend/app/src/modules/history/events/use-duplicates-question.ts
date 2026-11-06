import type { HistoryEventQuestion } from '@/modules/history/events/types';

/** The actions on duplicate groups that ask before they run. */
export const DuplicatesAction = {
  FIX: 'fix',
  MARK_NON_DUPLICATED: 'mark-non-duplicated',
  RESTORE: 'restore',
} as const;

export type DuplicatesAction = typeof DuplicatesAction[keyof typeof DuplicatesAction];

interface UseDuplicatesQuestionReturn {
  /**
   * What `action` asks beside its button before it runs on `count` groups.
   *
   * @remarks
   * One group gets the singular wording, which describes what the action does; more get the count.
   */
  duplicatesQuestion: (action: DuplicatesAction, count: number) => HistoryEventQuestion;
}

export function useDuplicatesQuestion(): UseDuplicatesQuestionReturn {
  const { t } = useI18n({ useScope: 'global' });

  function fixQuestion(count: number): HistoryEventQuestion {
    return count === 1
      ? { message: t('customized_event_duplicates.actions.fix_single_confirm'), title: t('customized_event_duplicates.actions.fix_single') }
      : { message: t('customized_event_duplicates.actions.fix_selected_confirm', { count }), title: t('customized_event_duplicates.actions.fix_selected') };
  }

  function markNonDuplicatedQuestion(count: number): HistoryEventQuestion {
    return count === 1
      ? { message: t('customized_event_duplicates.actions.mark_non_duplicated_confirm'), title: t('customized_event_duplicates.actions.mark_non_duplicated') }
      : { message: t('customized_event_duplicates.actions.mark_non_duplicated_selected_confirm', { count }), title: t('customized_event_duplicates.actions.mark_non_duplicated_selected') };
  }

  function restoreQuestion(count: number): HistoryEventQuestion {
    return count === 1
      ? { message: t('customized_event_duplicates.actions.restore_confirm'), title: t('customized_event_duplicates.actions.restore') }
      : { message: t('customized_event_duplicates.actions.restore_selected_confirm', { count }), title: t('customized_event_duplicates.actions.restore_selected') };
  }

  function duplicatesQuestion(action: DuplicatesAction, count: number): HistoryEventQuestion {
    switch (action) {
      case DuplicatesAction.FIX:
        return fixQuestion(count);
      case DuplicatesAction.MARK_NON_DUPLICATED:
        return markNonDuplicatedQuestion(count);
      case DuplicatesAction.RESTORE:
        return restoreQuestion(count);
    }
  }

  return { duplicatesQuestion };
}
