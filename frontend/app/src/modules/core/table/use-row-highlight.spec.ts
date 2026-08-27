import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';

interface Row {
  location: string;
  name: string;
}

const keyOf = (row: Row): string => `${row.location}#${row.name}`;

describe('useRowHighlight', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should not highlight any row initially', () => {
    const { isHighlighted, rowClass } = useRowHighlight<Row>(keyOf);
    const row = { location: 'kraken', name: 'main' };
    expect(isHighlighted(row)).toBe(false);
    expect(rowClass(row)).toBe('transition-colors duration-1000');
  });

  it('should highlight the matching row after highlight is called', () => {
    const { highlight, isHighlighted, rowClass } = useRowHighlight<Row>(keyOf);
    const target = { location: 'kraken', name: 'main' };
    const other = { location: 'binance', name: 'main' };

    highlight(target);

    expect(isHighlighted(target)).toBe(true);
    expect(isHighlighted(other)).toBe(false);
    expect(rowClass(target)).toContain('bg-rui-primary/[0.08]');
    expect(rowClass(other)).toBe('transition-colors duration-1000');
  });

  it('should clear the highlight once the duration elapses', () => {
    const { highlight, isHighlighted } = useRowHighlight<Row>(keyOf, { duration: 1000 });
    const target = { location: 'kraken', name: 'main' };

    highlight(target);
    expect(isHighlighted(target)).toBe(true);

    vi.advanceTimersByTime(999);
    expect(isHighlighted(target)).toBe(true);

    vi.advanceTimersByTime(1);
    expect(isHighlighted(target)).toBe(false);
  });

  it('should restart the timer when a new row is highlighted', () => {
    const { highlight, isHighlighted } = useRowHighlight<Row>(keyOf, { duration: 1000 });
    const first = { location: 'kraken', name: 'main' };
    const second = { location: 'binance', name: 'main' };

    highlight(first);
    vi.advanceTimersByTime(800);
    highlight(second);

    vi.advanceTimersByTime(800);
    expect(isHighlighted(second)).toBe(true);

    vi.advanceTimersByTime(200);
    expect(isHighlighted(second)).toBe(false);
  });

  it('should honour custom classes', () => {
    const { highlight, rowClass } = useRowHighlight<Row>(keyOf, {
      baseClass: 'base',
      highlightClass: 'flash',
    });
    const row = { location: 'kraken', name: 'main' };

    expect(rowClass(row)).toBe('base');
    highlight(row);
    expect(rowClass(row)).toBe('base flash');
  });
});
