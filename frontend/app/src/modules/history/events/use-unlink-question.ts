import type { HistoryEventQuestion } from '@/modules/history/events/types';

/** What is being unlinked, as far as the question asked before it cares. */
export type UnlinkKind = { type: 'asset-movement' } | { type: 'bridge'; hasSynthetic: boolean };

interface UseUnlinkQuestionReturn {
  unlinkQuestion: (kind: UnlinkKind) => HistoryEventQuestion;
}

/**
 * The question an unlink asks beside its button, worded for the kind of match it undoes.
 *
 * @remarks
 * A bridge match holding a counterpart rotki created says that unlinking deletes it.
 */
export function useUnlinkQuestion(): UseUnlinkQuestionReturn {
  const { t } = useI18n({ useScope: 'global' });

  function unlinkMessage(kind: UnlinkKind): string {
    if (kind.type === 'asset-movement')
      return t('transactions.events.confirmation.unlink.message');

    return kind.hasSynthetic
      ? t('transactions.events.confirmation.unlink.bridge_synthetic_message')
      : t('transactions.events.confirmation.unlink.bridge_message');
  }

  function unlinkQuestion(kind: UnlinkKind): HistoryEventQuestion {
    return {
      confirmLabel: t('transactions.events.actions.unlink'),
      message: unlinkMessage(kind),
      title: t('transactions.events.confirmation.unlink.title'),
    };
  }

  return { unlinkQuestion };
}
