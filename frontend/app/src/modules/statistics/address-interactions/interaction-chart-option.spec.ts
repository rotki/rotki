import type { DefaultLabelFormatterCallbackParams, GraphSeriesOption } from 'echarts';
import { graphOf, sceneOf } from '@test/utils/address-interactions';
import { createMock } from '@test/utils/create-mock';
import { assert, describe, expect, it } from 'vitest';
import { type InteractionGraph, transactionsOn } from './address-interaction-graph';
import { buildInteractionChartOption, type InteractionChartInput, sceneMetrics } from './interaction-chart-option';
import { focusOf, type InteractionFilters } from './interaction-scene';

const A = '0xaaaa';
const B = '0xbbbb';
const C = '0xcccc';

const colors = { dot: 'silver', labelSurface: 'rgba(255, 255, 255, 0.7)', muted: 'grey', selection: 'blue', surface: 'white', text: 'black' };

function params(dataIndex: number, dataType: 'node' | 'edge'): DefaultLabelFormatterCallbackParams {
  return createMock<DefaultLabelFormatterCallbackParams>({ dataIndex, dataType });
}

function input(graph: InteractionGraph, overrides: Partial<InteractionChartInput> = {}, filters: Partial<InteractionFilters> = {}): InteractionChartInput {
  const scene = sceneOf(graph, filters);
  return {
    avatarOf: () => undefined,
    colors,
    connectionColor: connection => `color:${connection.activity.map(({ chain }) => chain).join('+')}`,
    connectionTooltip: connection => `edge:${connection.id}`,
    description: 'description',
    highlightedConnectionIds: new Set(),
    isBareAddress: node => !node.address.startsWith('0x9'),
    nodeLabel: node => `label:${node.address}`,
    nodeTooltip: node => `<b>${node.address}</b>`,
    metrics: sceneMetrics(scene),
    positions: new Map(graph.nodes.map((node, index) => [node.id, { x: index * 10, y: index * 20 }])),
    scene,
    selectedNodeIds: new Set(),
    weightOf: connection => transactionsOn(connection, filters.chain),
    ...overrides,
  };
}

function build(graph: InteractionGraph, overrides: Partial<InteractionChartInput> = {}, filters: Partial<InteractionFilters> = {}): GraphSeriesOption {
  const [series] = [buildInteractionChartOption(input(graph, overrides, filters)).series].flat();
  assert(series?.type === 'graph');
  return series;
}

type NodeItem = Exclude<NonNullable<GraphSeriesOption['data']>[number], number | string | Date | unknown[] | null | undefined>;

function nodeItem(series: GraphSeriesOption, id: string): NodeItem {
  const item = series.data?.find(entry => typeof entry === 'object' && entry !== null && 'id' in entry && entry.id === id);
  assert(item && typeof item === 'object' && !Array.isArray(item) && !(item instanceof Date));
  return item;
}

const triangle = graphOf([
  { chain: 'eth', source: A, target: B, txHash: '0x1' },
  { chain: 'eth', source: A, target: B, txHash: '0x2' },
  { chain: 'eth', source: A, target: B, txHash: '0x3' },
  { chain: 'eth', source: A, target: B, txHash: '0x4' },
  { chain: 'optimism', source: A, target: B, txHash: '0x5' },
  { chain: 'eth', source: B, target: C, txHash: '0x6' },
]);

describe('interaction chart option', () => {
  it('should keep nodes and links in scene order so click indices map back to the scene', () => {
    const series = build(triangle);

    expect(series.data?.map(item => typeof item === 'object' && item !== null && 'id' in item ? item.id : undefined)).toEqual([A, B, C]);
    expect(series.links?.map(link => [link.source, link.target])).toEqual([[A, B], [B, C]]);
  });

  it('should draw the precomputed positions without running a layout of its own', () => {
    const series = build(triangle);

    expect(series.layout).toBe('none');
    expect([nodeItem(series, B).x, nodeItem(series, B).y]).toEqual([10, 20]);
  });

  it('should draw one link per pair, coloured by its chains and sized by every shared transaction', () => {
    const series = build(triangle);

    expect(series.links?.map(link => link.lineStyle?.color)).toEqual(['color:eth+optimism', 'color:eth']);
    expect(series.links?.map(link => link.lineStyle?.width)).toEqual([1.5 + Math.log2(5), 1.5]);
  });

  it('should size links by the picked chain only', () => {
    const series = build(triangle, {}, { chain: 'eth' });

    expect(series.links?.[0].lineStyle?.width).toBe(3.5);
  });

  it('should grey out connections and addresses the filters leave out, without moving them', () => {
    const series = build(triangle, {}, { minTransactions: 2 });

    expect(series.links?.map(link => link.lineStyle?.opacity)).toEqual([0.6, 0.07]);
    expect(nodeItem(series, C).itemStyle?.opacity).toBe(0.25);
    expect(nodeItem(series, C).emphasis?.disabled).toBe(true);
    expect([nodeItem(series, C).x, nodeItem(series, C).y]).toEqual([20, 40]);
  });

  it('should draw an address as its avatar once loaded, and as a plain circle before', () => {
    const series = build(triangle, { avatarOf: node => node.id === A ? 'data:image/png;base64,AAAA' : undefined });

    expect(nodeItem(series, A).symbol).toBe('image://data:image/png;base64,AAAA');
    expect(nodeItem(series, B).symbol).toBe('circle');
  });

  it('should dim everything outside the focus', () => {
    const graph = graphOf([
      { chain: 'eth', source: A, target: B, txHash: '0x1' },
      { chain: 'eth', source: '0xdddd', target: C, txHash: '0x2' },
    ]);
    const scene = sceneOf(graph);
    const series = build(graph, { focus: focusOf(scene, { nodeId: A }) });

    expect(nodeItem(series, A).itemStyle?.opacity).toBe(1);
    expect(nodeItem(series, B).itemStyle?.opacity).toBe(1);
    expect(nodeItem(series, C).itemStyle?.opacity).toBe(0.2);
    expect(series.links?.map(link => link.lineStyle?.opacity)).toEqual([0.6, 0.06]);
  });

  it('should label only the busiest addresses of a large graph, plus a small focus but not a crowded one', () => {
    const hub = '0x0000';
    const spokes = Array.from({ length: 14 }, (_, index) => `0x1${index.toString().padStart(3, '0')}`);
    const graph = graphOf([
      ...spokes.map(spoke => ({ chain: 'eth', source: hub, target: spoke, txHash: `0x${spoke}` })),
      { chain: 'eth', source: spokes[12], target: spokes[13], txHash: '0xpair' },
      { chain: 'eth', source: '0x9998', target: '0x9999', txHash: '0xlonely' },
    ]);

    const unfocused = build(graph);
    expect(nodeItem(unfocused, hub).label?.show).toBe(true);
    expect(nodeItem(unfocused, '0x9999').label?.show).toBe(false);

    const focused = build(graph, { focus: { connectionIds: new Set(), nodeIds: new Set(['0x9998', '0x9999']) } });
    expect(nodeItem(focused, '0x9999').label?.show).toBe(true);

    const crowd = build(graph, { focus: { connectionIds: new Set(), nodeIds: new Set(graph.nodes.map(({ id }) => id)) } });
    expect(nodeItem(crowd, '0x9999').label?.show).toBe(false);
  });

  it('should shrink nodes in a large graph so fitting it on screen does not pile them up', () => {
    const star = (size: number): InteractionGraph => graphOf(Array.from({ length: size }, (_, index) => ({ chain: 'eth', source: '0xhub', target: `0x${index}`, txHash: `0x${index}` })));
    const leafSize = (graph: InteractionGraph): unknown => nodeItem(build(graph), '0x0').symbolSize;

    expect(leafSize(star(20))).toBe(28);
    expect(leafSize(star(255))).toBeCloseTo(28 * 0.5 * 0.55);
  });

  it('should draw a large graph as plain dots, keeping identicons for the selection and a small focus', () => {
    const graph = graphOf(Array.from({ length: 70 }, (_, index) => ({ chain: 'eth', source: '0xhub', target: `0x${index}`, txHash: `0x${index}` })));
    const series = build(graph, {
      avatarOf: () => 'data:image/png;base64,AAAA',
      focus: { connectionIds: new Set(), nodeIds: new Set(['0x1', '0x2']) },
      selectedNodeIds: new Set(['0xhub']),
    });

    expect(nodeItem(series, '0x5').symbol).toBe('circle');
    expect(nodeItem(series, '0x1').symbol).toBe('image://data:image/png;base64,AAAA');
    expect(nodeItem(series, '0xhub').symbol).toBe('image://data:image/png;base64,AAAA');
  });

  it('should set bare addresses in monospace and names in the default font', () => {
    const series = build(triangle, { isBareAddress: node => node.id !== B });

    expect(nodeItem(series, A).label?.fontFamily).toContain('monospace');
    expect(nodeItem(series, B).label?.fontFamily).toBeUndefined();
  });

  it('should draw highlighted connections at full strength in the selection colour', () => {
    const series = build(triangle, { highlightedConnectionIds: new Set([triangle.connections[1].id]) });

    expect(series.links?.[1].lineStyle).toMatchObject({ color: 'blue', opacity: 1 });
  });

  it('should glow the selected addresses', () => {
    const series = build(triangle, { selectedNodeIds: new Set([A]) });

    expect(nodeItem(series, A).itemStyle?.shadowBlur).toBe(16);
    expect(nodeItem(series, B).itemStyle?.shadowBlur).toBe(0);
  });

  it('should render tooltips as rich text so address-book names never reach innerHTML', () => {
    const tooltip = [buildInteractionChartOption(input(triangle)).tooltip].flat()[0];
    assert(tooltip && typeof tooltip.formatter === 'function');

    expect(tooltip.renderMode).toBe('richText');
    expect(tooltip.formatter(params(2, 'node'), '')).toBe(`<b>${C}</b>`);
    expect(tooltip.formatter(params(1, 'edge'), '')).toBe(`edge:${triangle.connections[1].id}`);
  });

  it('should label nodes through the given formatter', () => {
    const label = build(triangle).label?.formatter;
    assert(typeof label === 'function');

    expect(label(params(0, 'node'))).toBe(`label:${A}`);
  });
});
