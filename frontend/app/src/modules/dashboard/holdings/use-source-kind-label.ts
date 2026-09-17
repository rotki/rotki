import { ExtraKind, SourceKind, type SummaryKind } from '@/modules/dashboard/holdings/core/holdings-types';

/** The legend name of a source kind. */
export function useSourceKindLabel(): (kind: SummaryKind) => string {
  const { t } = useI18n({ useScope: 'global' });

  return (kind: SummaryKind): string => {
    switch (kind) {
      case SourceKind.BLOCKCHAIN:
        return t('dashboard.holdings.kind.blockchain');
      case SourceKind.EXCHANGE:
        return t('dashboard.holdings.kind.exchange');
      case SourceKind.BANK:
        return t('dashboard.holdings.kind.bank');
      case SourceKind.MANUAL:
        return t('dashboard.holdings.kind.manual');
      case ExtraKind.NFT:
        return t('dashboard.holdings.kind.nft');
    }
  };
}
