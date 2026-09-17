import { ExtraKind, SourceKind, type SummaryKind } from '@/modules/dashboard/holdings/core/holdings-types';

/** The swatch each kind wears in the bar, the legend and the tile marks. */
export const SOURCE_KIND_COLOR: Record<SummaryKind, string> = {
  [SourceKind.BANK]: 'bg-emerald-500',
  [SourceKind.BLOCKCHAIN]: 'bg-blue-500',
  [SourceKind.EXCHANGE]: 'bg-orange-500',
  [SourceKind.MANUAL]: 'bg-amber-500',
  [ExtraKind.NFT]: 'bg-pink-400',
};
