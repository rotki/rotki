import type { ChainActivity, InteractionConnection, InteractionNode } from './address-interaction-graph';
import { Blockchain } from '@rotki/common';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useScramble } from '@/modules/settings/use-scramble';

/** Characters kept at each end of an address in a pair label, so both fit on one line of the side panel. */
export const PAIR_CHARS = 4;

/**
 * The longest name a graph label shows before it ends in an ellipsis. Cut by count rather than by an
 * ECharts `width`, which would stretch every label's background to that width.
 */
const CHART_LABEL_CHARS = 20;

/** An address's label, resolved once: the text to show and whether it is a name or the bare address. */
export interface AddressLabel {
  text: string;
  named: boolean;
}

interface UseInteractionLabelsReturn {
  /** The name or the address cut to `chars` characters at each end (6 by default), with which one it is. */
  addressLabelOf: (node: InteractionNode, chars?: number) => AddressLabel;
  /** Whether the address shows a name rather than the address itself. */
  hasName: (node: InteractionNode) => boolean;
  shortAddressLabel: (node: InteractionNode, chars?: number) => string;
  /** A graph label: the short label, with a long name ending in an ellipsis. */
  chartLabel: (node: InteractionNode) => string;
  /** The chain to resolve the address on so the name it shows matches this label. */
  namedChain: (node: InteractionNode) => string;
  connectionLabel: (connection: InteractionConnection) => string;
  /** Every chain's share of a pair on one line, naming the chain and the count. */
  activitySummary: (connection: InteractionConnection) => string;
  nodeTooltip: (node: InteractionNode) => string;
  connectionTooltip: (connection: InteractionConnection) => string;
}

/**
 * The labels every view of the graph shows for an address or a connection, so the canvas, the side
 * panel and their accessible names agree.
 *
 * @remarks
 * An address shows its name from the first of its chains that has one, then its ENS name, which does
 * not depend on the chain. While scrambling, names are dropped and the address itself is scrambled.
 */
export function useInteractionLabels(): UseInteractionLabelsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getAddressName, getEnsName } = useAddressNameResolution();
  const { getChainName } = useSupportedChains();
  const { scrambleAddress, scrambleData } = useScramble();

  /** The first chain with a name for the address, so a named address queues no further lookups. */
  function chainWithName(node: InteractionNode): { chain: string; name: string } | undefined {
    for (const chain of node.chains) {
      const name = getAddressName(node.address, chain);
      if (name)
        return { chain, name };
    }
    return undefined;
  }

  function addressName(node: InteractionNode): string | undefined {
    if (get(scrambleData))
      return undefined;
    return chainWithName(node)?.name ?? getEnsName(node.address) ?? undefined;
  }

  function addressLabelOf(node: InteractionNode, chars = 6): AddressLabel {
    const name = addressName(node);
    return name ? { named: true, text: name } : { named: false, text: truncateAddress(scrambleAddress(node.address), chars) };
  }

  function hasName(node: InteractionNode): boolean {
    return addressName(node) !== undefined;
  }

  function addressLabel(node: InteractionNode): string {
    return addressName(node) ?? scrambleAddress(node.address);
  }

  function shortAddressLabel(node: InteractionNode, chars = 6): string {
    return addressLabelOf(node, chars).text;
  }

  function chartLabel(node: InteractionNode): string {
    const label = shortAddressLabel(node);
    return label.length > CHART_LABEL_CHARS ? `${label.slice(0, CHART_LABEL_CHARS - 1)}…` : label;
  }

  function namedChain(node: InteractionNode): string {
    return chainWithName(node)?.chain ?? (getEnsName(node.address) ? Blockchain.ETH : node.chains[0]);
  }

  function pairLabel(connection: InteractionConnection): string {
    return `${addressLabel(connection.source)} ↔ ${addressLabel(connection.target)}`;
  }

  function connectionLabel(connection: InteractionConnection): string {
    return t('address_interactions.select_connection', {
      source: addressLabel(connection.source),
      target: addressLabel(connection.target),
    });
  }

  function activityLine({ chain, txHashes }: ChainActivity): string {
    return t('address_interactions.connection_summary', { chain: getChainName(chain), count: txHashes.length }, txHashes.length);
  }

  function activitySummary(connection: InteractionConnection): string {
    return connection.activity.map(activityLine).join(', ');
  }

  function nodeTooltip(node: InteractionNode): string {
    return `${addressLabel(node)}\n${node.chains.map(getChainName).join(', ')}`;
  }

  function connectionTooltip(connection: InteractionConnection): string {
    return [pairLabel(connection), ...connection.activity.map(activityLine)].join('\n');
  }

  return {
    activitySummary,
    addressLabelOf,
    chartLabel,
    connectionLabel,
    connectionTooltip,
    hasName,
    namedChain,
    nodeTooltip,
    shortAddressLabel,
  };
}
