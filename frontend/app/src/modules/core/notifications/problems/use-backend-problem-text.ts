import { toHumanReadable } from '@rotki/common';
import { type MessageKey, msg } from '@/message-key';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useLocations } from '@/modules/core/common/use-locations';
import { UserMessageKey } from '@/modules/core/messaging/types/base';
import {
  type BackendProblem,
  BALANCE_SNAPSHOT,
  type ProblemFamily,
  type ProblemItem,
  type ProblemSource,
} from '@/modules/core/notifications/problems/backend-problem-tree';
import {
  ENTRY_LABELS,
  FEATURE_LABELS,
  labelOf,
  OPERATION_LABELS,
  RECORD_LABELS,
} from '@/modules/core/notifications/problems/backend-problem-vocabulary';

/**
 * What an item is called, by family.
 *
 * @remarks
 * Most families name their item with a vocabulary label. A missing price names an asset and a
 * failed snapshot its date, which the drawer renders with the asset and date components rather
 * than as text.
 */
export type ProblemItemHeading =
  /** `full` is the untruncated text, for a heading shortened to fit the row. */
  | { readonly kind: 'text'; readonly text: string; readonly full?: string }
  | { readonly kind: 'asset'; readonly asset: string; readonly timestamp: number | null }
  | { readonly kind: 'date'; readonly date: Date };

/**
 * Shortens an asset identifier in the middle of its address, keeping the chain prefix and both ends.
 *
 * @remarks
 * Unknown assets of one exchange are often tokens of one chain, so cutting the end off would leave
 * every row reading the same `eip155:1/erc20:0x0000…`.
 */
function shortenIdentifier(identifier: string): string {
  const addressStart = identifier.lastIndexOf(':') + 1;
  return identifier.slice(0, addressStart) + truncateAddress(identifier.slice(addressStart));
}

interface UseBackendProblemTextReturn {
  /** The parent's title: its family, and the location when it has one. */
  problemTitle: (problem: BackendProblem) => string;
  /** The item's heading, rendered from its fields. */
  itemHeading: (item: ProblemItem) => ProblemItemHeading;
  /** What "copy details" copies: the backend's sentence, and the error when the sentence leaves it out. */
  itemDetails: (item: ProblemItem) => string;
}

const FAMILY_TITLES: Record<ProblemFamily, MessageKey> = {
  [BALANCE_SNAPSHOT]: msg.$t('backend_problems.title.balance_snapshot'),
  [UserMessageKey.BAD_DATA]: msg.$t('backend_problems.title.bad_data'),
  [UserMessageKey.INTERNAL]: msg.$t('backend_problems.title.internal'),
  [UserMessageKey.LOCAL_DB]: msg.$t('backend_problems.title.local_db'),
  [UserMessageKey.NETWORK]: msg.$t('backend_problems.title.network'),
  [UserMessageKey.PRICE]: msg.$t('backend_problems.title.price'),
  [UserMessageKey.UNKNOWN_ASSET]: msg.$t('backend_problems.title.unknown_asset'),
  [UserMessageKey.UNSUPPORTED]: msg.$t('backend_problems.title.unsupported'),
};

function errorOf(source: ProblemSource): string | undefined {
  switch (source.key) {
    case BALANCE_SNAPSHOT:
    case UserMessageKey.BAD_DATA:
    case UserMessageKey.NETWORK:
      return source.fields.error;
    case UserMessageKey.INTERNAL:
    case UserMessageKey.LOCAL_DB:
    case UserMessageKey.PRICE:
    case UserMessageKey.UNKNOWN_ASSET:
    case UserMessageKey.UNSUPPORTED:
      return undefined;
  }
}

/** Renders the backend problems tree as text, from each message's `key` and `fields`. */
export function useBackendProblemText(): UseBackendProblemTextReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getLocationData } = useLocations();

  function nameOf(identifier: string): string {
    return getLocationData(identifier)?.name ?? toHumanReadable(identifier, 'capitalize');
  }

  function problemTitle({ key, subject }: BackendProblem): string {
    const title = t(FAMILY_TITLES[key]);
    return subject ? t('backend_problems.with_subject', { subject: nameOf(subject), title }) : title;
  }

  /** The label for a vocabulary value, or the backend's sentence for a value this build does not know. */
  function labelled(labels: Record<string, MessageKey>, value: string, source: ProblemSource): ProblemItemHeading {
    const label = labelOf(labels, value);
    return { kind: 'text', text: label ? t(label) : source.value };
  }

  function itemHeading({ lastSeen, source }: ProblemItem): ProblemItemHeading {
    switch (source.key) {
      case BALANCE_SNAPSHOT:
        return { date: lastSeen, kind: 'date' };
      case UserMessageKey.PRICE:
        return source.fields.asset
          ? { asset: source.fields.asset, kind: 'asset', timestamp: source.fields.timestamp }
          : { kind: 'text', text: t('backend_problems.price_batch') };
      case UserMessageKey.UNKNOWN_ASSET:
        return { full: source.fields.identifier, kind: 'text', text: shortenIdentifier(source.fields.identifier) };
      case UserMessageKey.BAD_DATA:
      case UserMessageKey.NETWORK:
        return labelled(RECORD_LABELS, source.fields.record, source);
      case UserMessageKey.LOCAL_DB:
        return labelled(ENTRY_LABELS, source.fields.entry, source);
      case UserMessageKey.INTERNAL:
        return labelled(OPERATION_LABELS, source.fields.operation, source);
      case UserMessageKey.UNSUPPORTED:
        return labelled(FEATURE_LABELS, source.fields.feature, source);
    }
  }

  function itemDetails({ source }: ProblemItem): string {
    const error = errorOf(source);
    return error && !source.value.includes(error) ? `${source.value}\n${error}` : source.value;
  }

  return {
    itemDetails,
    itemHeading,
    problemTitle,
  };
}
