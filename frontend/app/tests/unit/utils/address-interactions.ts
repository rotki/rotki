import type { VueWrapper } from '@vue/test-utils';
import type { EChartsOption, GraphSeriesOption } from 'echarts';
import type { AddressInteraction } from '@/modules/statistics/address-interactions/address-interaction-types';
import { assert } from 'vitest';
import { createAddressInteractionGraph, type InteractionGraph } from '@/modules/statistics/address-interactions/address-interaction-graph';
import { activateScene, drawGraph, type InteractionFilters, type InteractionScene } from '@/modules/statistics/address-interactions/interaction-scene';

export const SOURCE = '0x1111111111111111111111111111111111111111';

export const TARGET = '0x2222222222222222222222222222222222222222';

export const OTHER = '0x3333333333333333333333333333333333333333';

/** A `RuiButton` that renders a plain button forwarding clicks, so specs can trigger it. */
export const ClickButtonStub = {
  emits: ['click'],
  template: '<button type="button" v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
};

export function interaction(chain = 'eth', txHash = '0xeth-transaction', source = SOURCE, target = TARGET): AddressInteraction {
  return { chain, source, target, txHash };
}

/** Interactions on `eth`, each pair repeated `count` times (one by default) with distinct hashes. */
export function links(...pairs: [source: string, target: string, count?: number][]): AddressInteraction[] {
  return pairs.flatMap(([source, target, count = 1]) =>
    Array.from({ length: count }, (_, index) => interaction('eth', `${source}-${target}-${index}`, source, target)));
}

export function graphOf(interactions: readonly AddressInteraction[]): InteractionGraph {
  return createAddressInteractionGraph(interactions);
}

/** The scene of a graph with nothing hidden and, unless overridden, every connection active. */
export function sceneOf(graph: InteractionGraph, filters: Partial<InteractionFilters> = {}, hiddenIds: ReadonlySet<string> = new Set()): InteractionScene {
  return activateScene(drawGraph(graph, hiddenIds), { minTransactions: 1, ...filters });
}

/** The graph series of the option a mounted `VChart` stub received. */
export function graphSeries(wrapper: VueWrapper): GraphSeriesOption {
  const option: EChartsOption = wrapper.getComponent({ name: 'VChart' }).props('option');
  const [series] = [option.series].flat();
  assert(series?.type === 'graph');
  return series;
}
