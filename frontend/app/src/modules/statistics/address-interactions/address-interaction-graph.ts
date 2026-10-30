import type { AddressInteraction } from './address-interaction-types';

export interface InteractionNode {
  id: string;
  chains: string[];
  address: string;
  x: number;
  y: number;
}

export interface InteractionConnection {
  id: string;
  chain: string;
  source: InteractionNode;
  target: InteractionNode;
  txHashes: string[];
}

export interface InteractionGraph {
  nodes: InteractionNode[];
  connections: InteractionConnection[];
  size: number;
}

interface GraphComponent {
  nodes: InteractionNode[];
  width: number;
  height: number;
}

function layoutComponent(root: InteractionNode, remaining: Set<InteractionNode>, neighbors: Map<string, Set<InteractionNode>>): GraphComponent {
  let layer = [root];
  remaining.delete(root);
  const layers: InteractionNode[][] = [];
  while (layer.length > 0) {
    layers.push(layer);
    const next: InteractionNode[] = [];
    for (const node of layer) {
      for (const neighbor of neighbors.get(node.id)!) {
        if (remaining.delete(neighbor))
          next.push(neighbor);
      }
    }
    layer = next.sort((a, b) => a.id.localeCompare(b.id));
  }
  const rows = Math.max(...layers.map(layer => layer.length));
  layers.forEach((layer, column) => {
    layer.forEach((node, row) => {
      node.x = 110 + column * 200;
      node.y = 50 + row * 110 + (rows - layer.length) * 55;
    });
  });
  return { nodes: layers.flat(), width: layers.length * 200 + 20, height: rows * 110 + 40 };
}

function layoutGraph(nodes: InteractionNode[], connections: Iterable<InteractionConnection>): number {
  const neighbors = new Map(nodes.map(node => [node.id, new Set<InteractionNode>()]));
  for (const connection of connections) {
    neighbors.get(connection.source.id)!.add(connection.target);
    neighbors.get(connection.target.id)!.add(connection.source);
  }
  const remaining = new Set(nodes);
  const components: GraphComponent[] = [];
  while (remaining.size > 0) {
    const root = [...remaining].sort((a, b) => neighbors.get(b.id)!.size - neighbors.get(a.id)!.size || a.id.localeCompare(b.id))[0];
    components.push(layoutComponent(root, remaining, neighbors));
  }
  const targetWidth = Math.max(440, Math.sqrt(components.reduce((area, component) => area + component.width * component.height, 0) * 1.6));
  let left = 0;
  let top = 0;
  let rowHeight = 0;
  let width = 0;
  for (const component of components) {
    if (left > 0 && left + component.width > targetWidth) {
      top += rowHeight;
      left = 0;
      rowHeight = 0;
    }
    for (const node of component.nodes) {
      node.x += left;
      node.y += top;
    }
    left += component.width;
    width = Math.max(width, left);
    rowHeight = Math.max(rowHeight, component.height);
  }
  return Math.max(width, top + rowHeight);
}

export function createAddressInteractionGraph(interactions: readonly AddressInteraction[]): InteractionGraph {
  const nodes = new Map<string, InteractionNode>();
  const connections = new Map<string, InteractionConnection>();

  function node(chain: string, address: string): InteractionNode {
    const id = address;
    let result = nodes.get(id);
    if (!result) {
      result = { address, chains: [], id, x: 0, y: 0 };
      nodes.set(id, result);
    }
    if (!result.chains.includes(chain))
      result.chains.push(chain);
    return result;
  }

  for (const interaction of interactions) {
    const { chain, txHash } = interaction;
    if (interaction.source === interaction.target)
      continue;

    const source = interaction.source < interaction.target ? interaction.source : interaction.target;
    const target = interaction.source < interaction.target ? interaction.target : interaction.source;
    const id = JSON.stringify([chain, source, target]);
    let connection = connections.get(id);
    if (!connection) {
      connection = { chain, id, source: node(chain, source), target: node(chain, target), txHashes: [] };
      connections.set(id, connection);
    }
    if (!connection.txHashes.includes(txHash))
      connection.txHashes.push(txHash);
  }

  const sortedNodes = [...nodes.values()].sort((a, b) => a.id.localeCompare(b.id));
  for (const node of sortedNodes)
    node.chains.sort();
  const size = layoutGraph(sortedNodes, connections.values());

  const sortedConnections = [...connections.values()].sort((a, b) => a.id.localeCompare(b.id));
  for (const connection of sortedConnections)
    connection.txHashes.sort();

  return { connections: sortedConnections, nodes: sortedNodes, size };
}
