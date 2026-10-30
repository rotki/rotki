import { describe, expect, it } from 'vitest';
import { createAddressInteractionGraph, type InteractionNode } from './address-interaction-graph';
import { routeInteractionEdge } from './interaction-edge-routing';

function node(id: string, x: number, y: number): InteractionNode {
  return { id, address: id, chains: ['eth'], x, y };
}

function expectClearance(path: string, obstacles: InteractionNode[], top: number = -34): void {
  const coordinates = path.match(/-?\d+(?:\.\d+)?/g)!.map(Number);
  for (let index = 2; index < coordinates.length; index += 2) {
    for (let step = 0; step <= 100; step++) {
      const t = step / 100;
      const x = coordinates[index - 2] * (1 - t) + coordinates[index] * t;
      const y = coordinates[index - 1] * (1 - t) + coordinates[index + 1] * t;
      for (const obstacle of obstacles) {
        const inside = x > obstacle.x - 90 && x < obstacle.x + 90 && y > obstacle.y + top && y < obstacle.y + 72;
        expect(inside, `Edge crosses ${obstacle.id} at ${x}, ${y}`).toBe(false);
      }
    }
  }
}

describe('interaction edge clearance', () => {
  it('should leave vertical endpoints without crossing their address labels', () => {
    const source = node('source', 310, 50);
    const target = node('target', 310, 270);
    const route = routeInteractionEdge(source, target, [source, target], 0, 1);

    expectClearance(route.path, [source, target], 28);
  });

  it('should detour around an unrelated address and its labels rather than imply a connection', () => {
    const source = node('source', 110, 180);
    const target = node('target', 590, 180);
    const unrelated = node('unrelated', 350, 180);
    const route = routeInteractionEdge(source, target, [source, unrelated, target], 0, 1);

    expectClearance(route.path, [unrelated]);
  });

  it('should avoid label rows even when the edge clears the node circle', () => {
    const source = node('source', 110, 230);
    const target = node('target', 590, 230);
    const unrelated = node('unrelated', 350, 180);
    const route = routeInteractionEdge(source, target, [source, unrelated, target], 0, 1);

    expectClearance(route.path, [unrelated]);
  });

  it('should route separate chains around overlapping obstacle clearances', () => {
    const source = node('source', 110, 180);
    const target = node('target', 710, 180);
    const obstacles = [node('first', 310, 150), node('second', 510, 210)];
    const routes = [0, 1].map(index => routeInteractionEdge(source, target, [source, ...obstacles, target], index, 2));

    for (const route of routes)
      expectClearance(route.path, obstacles);
    expect(routes[0].path).not.toBe(routes[1].path);
  });

  it('should route every parallel connection when padded obstacles of neighbours overlap', () => {
    const graph = createAddressInteractionGraph([
      { chain: 'polygon_pos', source: 'C', target: 'D', txHash: '0x1' },
      { chain: 'polygon_pos', source: 'C', target: 'B', txHash: '0x2' },
      { chain: 'base', source: 'A', target: 'D', txHash: '0x3' },
      { chain: 'optimism', source: 'A', target: 'D', txHash: '0x4' },
      { chain: 'polygon_pos', source: 'A', target: 'D', txHash: '0x5' },
    ]);
    const parallel = graph.connections.filter(({ source, target }) => source.id === 'A' && target.id === 'D');

    expect(parallel).toHaveLength(3);
    const unrelated = graph.nodes.filter(({ id }) => id === 'B');
    for (const [index, { source, target }] of parallel.entries()) {
      const route = routeInteractionEdge(source, target, graph.nodes, index, parallel.length);
      expect(Number.isFinite(route.labelX) && Number.isFinite(route.labelY)).toBe(true);
      expectClearance(route.path, unrelated);
    }
  });

  it('should keep the direct curve instead of searching when too many addresses surround an edge', () => {
    const source = node('source', 110, 600);
    const target = node('target', 310, 600);
    const crowd = Array.from({ length: 40 }, (_, row) => node(`crowd-${row}`, 210, row * 30));
    const route = routeInteractionEdge(source, target, [source, target, ...crowd], 0, 1);

    expect(route.path).toMatch(/^M 110 600 Q /);
  });
});
