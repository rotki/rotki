import type { RuiIcons } from '@rotki/ui-library';
import type { SpamSignal } from '@/modules/assets/api/use-asset-spam-prediction-api';

interface SpamSignalDescription {
  icon: RuiIcons;
  text: string;
}

type Describe = (signal: SpamSignal) => SpamSignalDescription;

export function useSpamSignal(): Describe {
  const { t } = useI18n({ useScope: 'global' });

  function source(field: SpamSignal['field']): string {
    return field === 'name' ? t('spam_estimate.traits.name') : t('spam_estimate.traits.symbol');
  }

  const descriptions: Record<SpamSignal['code'], Describe> = {
    combining_marks: ({ field }) => ({ icon: 'lu-type', text: t('spam_estimate.traits.marks', { source: source(field) }) }),
    common_symbol: () => ({ icon: 'lu-copy', text: t('spam_estimate.traits.common_symbol') }),
    in_collection: () => ({ icon: 'lu-layers', text: t('spam_estimate.traits.in_collection') }),
    in_packaged_globaldb: () => ({ icon: 'lu-database', text: t('spam_estimate.traits.in_database') }),
    invisible_characters: ({ field }) => ({ icon: 'lu-eye-off', text: t('spam_estimate.traits.invisible', { source: source(field) }) }),
    known_origin_unavailable: () => ({ icon: 'lu-circle-help', text: t('spam_estimate.traits.origin') }),
    lookalike_symbol: () => ({ icon: 'lu-copy', text: t('spam_estimate.traits.lookalike') }),
    max_token_transfers: ({ value }) => ({ icon: 'lu-arrow-left-right', text: t('spam_estimate.traits.max_transfers', { count: value ?? 0 }) }),
    mean_token_transfers: ({ value }) => ({ icon: 'lu-arrow-left-right', text: t('spam_estimate.traits.mean_transfers', { count: value ?? 0 }) }),
    mixed_scripts: ({ field }) => ({ icon: 'lu-languages', text: t('spam_estimate.traits.scripts', { source: source(field) }) }),
    non_ascii: ({ field }) => ({ icon: 'lu-languages', text: t('spam_estimate.traits.unicode', { source: source(field) }) }),
    not_in_collection: () => ({ icon: 'lu-layers', text: t('spam_estimate.traits.not_in_collection') }),
    not_in_packaged_globaldb: () => ({ icon: 'lu-database', text: t('spam_estimate.traits.not_in_database') }),
    promotion: ({ field }) => ({ icon: 'lu-megaphone', text: t('spam_estimate.traits.promotion', { source: source(field) }) }),
    url: ({ field }) => ({ icon: 'lu-link', text: t('spam_estimate.traits.link', { source: source(field) }) }),
  };

  return signal => descriptions[signal.code](signal);
}
