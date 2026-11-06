import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';

/**
 * What a delete button asks before it deletes.
 *
 * @remarks
 * A {@link ConfirmQuestion} whose `confirmLabel` may be left out: {@link useDeleteQuestion} then
 * labels the accept button "Delete", and an unset `tone` is `error` rather than `warning`, since
 * every delete destroys data. Producers name only what is deleted and what deleting it means; a full
 * `ConfirmQuestion` is accepted as it is, so a producer shared with another consumer can return one.
 */
export type RowDeleteQuestion = Omit<ConfirmQuestion, 'confirmLabel'> & { readonly confirmLabel?: string };

/**
 * Completes a delete question with the "Delete" label and the `error` tone it leaves out.
 */
export function useDeleteQuestion(): (question: RowDeleteQuestion) => ConfirmQuestion {
  const { t } = useI18n({ useScope: 'global' });
  return question => ({
    ...question,
    confirmLabel: question.confirmLabel ?? t('common.actions.delete'),
    tone: question.tone ?? 'error',
  });
}
