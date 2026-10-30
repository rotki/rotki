import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, nextTick, type Ref, ref } from 'vue';
import { createAddressInteractionGraph, type InteractionGraph } from './address-interaction-graph';
import { type RoutedConnection, useInteractionRoutes } from './use-interaction-routes';

function star(size: number): InteractionGraph {
  return createAddressInteractionGraph(Array.from({ length: size }, (_, index) => ({
    chain: 'eth',
    source: 'hub',
    target: `leaf-${String(index).padStart(3, '0')}`,
    txHash: `0x${index}`,
  })));
}

function withRoutes(graph: () => InteractionGraph): { routes: Readonly<Ref<readonly RoutedConnection[]>>; stop: () => void } {
  const holder: { routes?: Readonly<Ref<readonly RoutedConnection[]>> } = {};
  const app = createApp({
    render: () => null,
    setup: (): void => {
      holder.routes = useInteractionRoutes(graph);
    },
  });
  app.mount(document.createElement('div'));
  assert(holder.routes);
  return { routes: holder.routes, stop: () => app.unmount() };
}

describe('use-interaction-routes', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should start with direct curves and replace them with detours once refined', async () => {
    const { routes, stop } = withRoutes(() => star(60));

    expect(routes.value).toHaveLength(60);
    expect(routes.value.every(({ path }) => path.includes(' Q '))).toBe(true);

    await vi.runAllTimersAsync();
    expect(routes.value).toHaveLength(60);
    expect(routes.value.some(({ path }) => path.includes(' L '))).toBe(true);
    stop();
  });

  it('should keep the same route object for a connection whose curve needs no detour', async () => {
    const { routes, stop } = withRoutes(() => star(60));
    const initial = new Map(routes.value.map(route => [route.connection.id, route]));

    await vi.runAllTimersAsync();
    const unchanged = routes.value.filter(({ path }) => path.includes(' Q '));
    expect(unchanged.length).toBeGreaterThan(0);
    for (const route of unchanged)
      expect(route).toBe(initial.get(route.connection.id));
    stop();
  });

  it('should not let the batch of a replaced graph overwrite the routes of the new one', async () => {
    const replacement = star(3);
    const graph = ref<InteractionGraph>(star(40));
    const { routes, stop } = withRoutes(() => graph.value);

    graph.value = replacement;
    await nextTick();
    await vi.advanceTimersToNextTimerAsync();

    expect(routes.value.map(({ connection }) => connection)).toEqual(replacement.connections);
    stop();
  });
});
