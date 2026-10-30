import type { Ref } from 'vue';
import type { InteractionConnection, InteractionGraph } from './address-interaction-graph';
import { startPromise } from '@shared/utils';
import { directInteractionEdge, type EdgeRoute, routeInteractionEdge } from './interaction-edge-routing';

export interface RoutedConnection extends EdgeRoute {
  connection: InteractionConnection;
}

interface RouteJob {
  connection: InteractionConnection;
  index: number;
  count: number;
}

/** How long one batch may hold the main thread before yielding to rendering and input. */
const BATCH_BUDGET_MS = 8;
/** Minimum time between published updates, so the canvas re-renders a few times rather than once per batch. */
const PUBLISH_INTERVAL_MS = 100;

function planJobs(connections: readonly InteractionConnection[]): RouteJob[] {
  const pairs = new Map<string, InteractionConnection[]>();
  for (const connection of connections) {
    const key = JSON.stringify([connection.source.id, connection.target.id]);
    const pair = pairs.get(key) ?? [];
    pair.push(connection);
    pairs.set(key, pair);
  }
  return [...pairs.values()].flatMap(pair => pair.map((connection, index) => ({ connection, count: pair.length, index })));
}

async function nextTask(): Promise<void> {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, 0);
  });
}

/**
 * Routes every connection of the graph without blocking the page.
 *
 * @remarks
 * Every connection first gets its direct curve, which costs no obstacle search, so the graph is
 * usable at once. Detours around other addresses are then computed in time-boxed batches that
 * yield between each other. The improved curves are published at most every
 * {@link PUBLISH_INTERVAL_MS} and once more at the end. A connection whose route did not change
 * keeps its previous object, so the canvas can skip re-rendering it. A new graph abandons the
 * batches still pending for the previous one.
 */
export function useInteractionRoutes(graph: () => InteractionGraph): Readonly<Ref<readonly RoutedConnection[]>> {
  const routes = shallowRef<RoutedConnection[]>([]);

  async function refine(jobs: RouteJob[], nodes: InteractionGraph['nodes'], current: () => boolean): Promise<void> {
    const refined = [...get(routes)];
    let position = 0;
    let changed = false;
    let published = performance.now();
    while (position < jobs.length) {
      const deadline = performance.now() + BATCH_BUDGET_MS;
      while (position < jobs.length && performance.now() < deadline) {
        const { connection, count, index } = jobs[position];
        const route = routeInteractionEdge(connection.source, connection.target, nodes, index, count);
        if (route.path !== refined[position].path) {
          refined[position] = { connection, ...route };
          changed = true;
        }
        position++;
      }
      await nextTask();
      if (!current())
        return;
      const finished = position >= jobs.length;
      if (changed && (finished || performance.now() - published >= PUBLISH_INTERVAL_MS)) {
        set(routes, [...refined]);
        changed = false;
        published = performance.now();
      }
    }
  }

  watch(graph, (value) => {
    let active = true;
    onWatcherCleanup(() => {
      active = false;
    });
    const jobs = planJobs(value.connections);
    set(routes, jobs.map(({ connection, count, index }): RoutedConnection => ({
      connection,
      ...directInteractionEdge(connection.source, connection.target, index, count),
    })));
    startPromise(refine(jobs, value.nodes, () => active));
  }, { immediate: true });

  return shallowReadonly(routes);
}
