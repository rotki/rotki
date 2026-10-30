import type { InteractionNode } from './address-interaction-graph';

interface Point {
  x: number;
  y: number;
}

interface Obstacle {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export interface EdgeRoute {
  path: string;
  labelX: number;
  labelY: number;
}

function intersects(start: Point, end: Point, obstacle: Obstacle): boolean {
  let from = 0;
  let to = 1;
  for (const [origin, delta, low, high] of [
    [start.x, end.x - start.x, obstacle.left, obstacle.right],
    [start.y, end.y - start.y, obstacle.top, obstacle.bottom],
  ]) {
    if (delta === 0) {
      if (origin <= low || origin >= high)
        return false;
    }
    else {
      const first = (low - origin) / delta;
      const last = (high - origin) / delta;
      from = Math.max(from, Math.min(first, last));
      to = Math.min(to, Math.max(first, last));
      if (from >= to - 1e-9)
        return false;
    }
  }
  return from < to - 1e-9;
}

function nearestUnvisited(distances: number[], visited: Set<number>): number {
  let nearest = -1;
  for (let index = 0; index < distances.length; index++) {
    if (!visited.has(index) && (nearest === -1 || distances[index] < distances[nearest]))
      nearest = index;
  }
  return nearest;
}

function shortestRoute(source: Point, target: Point, obstacles: Obstacle[]): Point[] | undefined {
  const points = [source, target, ...obstacles.flatMap(({ left, right, top, bottom }) => [
    { x: left, y: top },
    { x: right, y: top },
    { x: left, y: bottom },
    { x: right, y: bottom },
  ])];
  const distances = points.map(() => Number.POSITIVE_INFINITY);
  const estimates = [...distances];
  const remaining = points.map(point => Math.hypot(target.x - point.x, target.y - point.y));
  const previous = points.map(() => -1);
  const visited = new Set<number>();
  distances[0] = 0;
  estimates[0] = remaining[0];
  while (true) {
    const current = nearestUnvisited(estimates, visited);
    if (current === -1 || !Number.isFinite(distances[current]))
      return undefined;
    if (current === 1)
      break;
    visited.add(current);
    for (let next = 0; next < points.length; next++) {
      if (visited.has(next))
        continue;
      const distance = distances[current] + Math.hypot(points[next].x - points[current].x, points[next].y - points[current].y);
      if (distance >= distances[next] || obstacles.some(obstacle => intersects(points[current], points[next], obstacle)))
        continue;
      distances[next] = distance;
      estimates[next] = distance + remaining[next];
      previous[next] = current;
    }
  }
  const route: Point[] = [];
  for (let current = 1; current !== -1; current = previous[current])
    route.push(points[current]);
  return route.reverse();
}

/** Obstacles beyond this many make the visibility search too costly, so the edge keeps its curve. */
const MAX_DETOUR_OBSTACLES = 12;
/** How far past the edge's own bounding box an obstacle can still shape a detour. */
const DETOUR_MARGIN = 120;

function obstacleFor(node: InteractionNode, endpoint: boolean, padding: number): Obstacle {
  return {
    left: node.x - 92 - padding,
    right: node.x + 92 + padding,
    top: node.y + (endpoint ? 28 : -36 - padding),
    bottom: node.y + 74 + padding,
  };
}

function overlaps(obstacle: Obstacle, area: Obstacle): boolean {
  return obstacle.left < area.right && obstacle.right > area.left && obstacle.top < area.bottom && obstacle.bottom > area.top;
}

function quadraticSamples(source: Point, control: Point, target: Point): Point[] {
  return Array.from({ length: 33 }, (_, step): Point => {
    const t = step / 32;
    return {
      x: (1 - t) ** 2 * source.x + 2 * (1 - t) * t * control.x + t ** 2 * target.x,
      y: (1 - t) ** 2 * source.y + 2 * (1 - t) * t * control.y + t ** 2 * target.y,
    };
  });
}

function labelOf(route: Point[], fallback: Point): Point {
  let longest = 0;
  let label = fallback;
  for (let step = 1; step < route.length; step++) {
    const start = route[step - 1];
    const end = route[step];
    const length = Math.hypot(end.x - start.x, end.y - start.y);
    if (length > longest) {
      longest = length;
      label = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };
    }
  }
  return label;
}

/**
 * Routes an edge outside unrelated node bodies and their two label rows.
 *
 * @remarks
 * Never throws: the padding that keeps parallel edges apart can make neighbouring obstacles overlap
 * and wall an endpoint in, so a blocked search is retried without padding, and an edge that still
 * has no route (or sits among too many obstacles to search) keeps its direct curve.
 */
export function routeInteractionEdge(source: InteractionNode, target: InteractionNode, nodes: readonly InteractionNode[], index: number, count: number): EdgeRoute {
  const distance = Math.hypot(target.x - source.x, target.y - source.y);
  const offset = (index - (count - 1) / 2) * 64;
  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2;
  const control = {
    x: midX - (target.y - source.y) / distance * offset,
    y: midY + (target.x - source.x) / distance * offset,
  };
  const samples = quadraticSamples(source, control, target);
  const area: Obstacle = {
    left: Math.min(...samples.map(point => point.x)) - DETOUR_MARGIN,
    right: Math.max(...samples.map(point => point.x)) + DETOUR_MARGIN,
    top: Math.min(...samples.map(point => point.y)) - DETOUR_MARGIN,
    bottom: Math.max(...samples.map(point => point.y)) + DETOUR_MARGIN,
  };
  const nearby = nodes.filter(node => overlaps(obstacleFor(node, false, 0), area));
  const obstaclesAt = (padding: number): Obstacle[] =>
    nearby.map(node => obstacleFor(node, node.id === source.id || node.id === target.id, padding));

  const padding = 14 * index / count;
  const padded = obstaclesAt(padding);
  const curve: EdgeRoute = {
    path: `M ${source.x} ${source.y} Q ${control.x} ${control.y} ${target.x} ${target.y}`,
    labelX: (midX + control.x) / 2,
    labelY: (midY + control.y) / 2,
  };
  if (!samples.some((point, step) => step > 0 && padded.some(obstacle => intersects(samples[step - 1], point, obstacle))))
    return curve;
  if (nearby.length > MAX_DETOUR_OBSTACLES)
    return curve;

  const route = shortestRoute(source, target, padded) ?? shortestRoute(source, target, obstaclesAt(0));
  if (!route)
    return curve;

  const label = labelOf(route, { x: midX, y: midY });
  return {
    path: route.map((point, step) => `${step === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' '),
    labelX: label.x,
    labelY: label.y,
  };
}
