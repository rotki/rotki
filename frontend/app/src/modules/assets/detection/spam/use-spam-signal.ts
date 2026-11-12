import type { RuiIcons } from '@rotki/ui-library';

interface SpamSignal {
  icon: RuiIcons;
  text: string;
}

export function useSpamSignal(): (signal: string) => SpamSignal {
  const { t } = useI18n({ useScope: 'global' });

  function describeMetadata(field: string, detail: string): SpamSignal | undefined {
    const source = field === 'name'
      ? t('asset_table.newly_detected.spam.traits.name')
      : t('asset_table.newly_detected.spam.traits.symbol');

    switch (detail) {
      case 'contains URL-like text':
        return { icon: 'lu-link', text: t('asset_table.newly_detected.spam.traits.link', { source }) };
      case 'contains promotional wording':
        return { icon: 'lu-megaphone', text: t('asset_table.newly_detected.spam.traits.promotion', { source }) };
      case 'contains non-ASCII characters':
        return { icon: 'lu-languages', text: t('asset_table.newly_detected.spam.traits.unicode', { source }) };
      case 'contains invisible formatting characters':
        return { icon: 'lu-eye-off', text: t('asset_table.newly_detected.spam.traits.invisible', { source }) };
      case 'contains combining marks':
        return { icon: 'lu-type', text: t('asset_table.newly_detected.spam.traits.marks', { source }) };
      case 'contains multiple writing scripts':
        return { icon: 'lu-languages', text: t('asset_table.newly_detected.spam.traits.scripts', { source }) };
      case 'matches a common symbol spelling; authenticity is unknown':
        return { icon: 'lu-copy', text: t('asset_table.newly_detected.spam.traits.common_symbol') };
      case 'visual/compatibility skeleton matches a common symbol; authenticity is unknown':
        return { icon: 'lu-copy', text: t('asset_table.newly_detected.spam.traits.lookalike') };
      default:
        return undefined;
    }
  }

  function describeContext(signal: string, detail: string): SpamSignal | undefined {
    if (detail === 'known-origin fraction is unavailable')
      return { icon: 'lu-circle-help', text: t('asset_table.newly_detected.spam.traits.origin') };

    const transfers = signal.match(/context: (maximum|mean) same-token ERC-20 Transfer events (?:within one transaction|per observed transaction): ([\d.e+-]+);/);
    if (transfers) {
      return {
        icon: 'lu-arrow-left-right',
        text: transfers[1] === 'maximum'
          ? t('asset_table.newly_detected.spam.traits.max_transfers', { count: transfers[2] })
          : t('asset_table.newly_detected.spam.traits.mean_transfers', { count: transfers[2] }),
      };
    }

    switch (detail) {
      case 'present in packaged globaldb; not an authenticity guarantee':
        return { icon: 'lu-database', text: t('asset_table.newly_detected.spam.traits.in_database') };
      case 'not present in packaged globaldb; not an authenticity guarantee':
        return { icon: 'lu-database', text: t('asset_table.newly_detected.spam.traits.not_in_database') };
      case 'present in an asset collection; not an authenticity guarantee':
        return { icon: 'lu-layers', text: t('asset_table.newly_detected.spam.traits.in_collection') };
      case 'not present in an asset collection; not an authenticity guarantee':
        return { icon: 'lu-layers', text: t('asset_table.newly_detected.spam.traits.not_in_collection') };
      default:
        return undefined;
    }
  }

  return (signal: string): SpamSignal => {
    const [field, detail = ''] = signal.split(': ');
    let description: SpamSignal | undefined;
    if (field === 'name' || field === 'symbol')
      description = describeMetadata(field, detail);
    else if (field === 'context')
      description = describeContext(signal, detail);

    return description ?? { icon: 'lu-info', text: signal };
  };
}
