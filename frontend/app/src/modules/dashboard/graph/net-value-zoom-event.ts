import type { NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';

/**
 * The zoom bounds carried by an ECharts `datazoom` event, flattened out of either shape it emits.
 *
 * @remarks
 * An inside-zoom nests these in a `batch` array while a slider drag puts them at the top level.
 * `startValue` and `endValue` are axis values in milliseconds; `start` and `end` are percentages
 * of the x-axis range, 0 to 100. A slider drag commonly supplies only the percentages.
 */
interface ZoomFields {
  startValue?: unknown;
  endValue?: unknown;
  start?: unknown;
  end?: unknown;
}

function isObjectValue(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function readZoomFields(event: unknown): ZoomFields | undefined {
  if (isObjectValue(event) && 'batch' in event && Array.isArray(event.batch) && event.batch.length > 0) {
    const first = event.batch[0];
    if (!isObjectValue(first))
      return undefined;
    return { end: first.end, endValue: first.endValue, start: first.start, startValue: first.startValue };
  }
  if (isObjectValue(event))
    return { end: event.end, endValue: event.endValue, start: event.start, startValue: event.startValue };
  return undefined;
}

const ZOOM_MS = 1000;

export function resolveZoomRange(fields: ZoomFields | undefined, times: number[]): NetValueZoomRange | undefined {
  if (typeof fields?.startValue === 'number' && typeof fields?.endValue === 'number') {
    return { end: Math.ceil(fields.endValue / ZOOM_MS), start: Math.floor(fields.startValue / ZOOM_MS) };
  }
  if (typeof fields?.start === 'number' && typeof fields?.end === 'number') {
    const first = times[0];
    const last = times.at(-1);
    if (last === undefined)
      return undefined;
    const span = last - first;
    return {
      end: Math.ceil(first + (span * fields.end) / 100),
      start: Math.floor(first + (span * fields.start) / 100),
    };
  }
  return undefined;
}
