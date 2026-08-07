import { describe, expect, it } from 'vitest';
import { formatElapsed } from './elapsed';

describe('formatElapsed', () => {
  it('should show whole seconds under a minute', () => {
    expect(formatElapsed(0)).toBe('0s');
    expect(formatElapsed(14_400)).toBe('14s');
    expect(formatElapsed(59_999)).toBe('59s');
  });

  it('should pad the seconds once minutes appear, so the column does not jump', () => {
    expect(formatElapsed(60_000)).toBe('1m 00s');
    expect(formatElapsed(192_000)).toBe('3m 12s');
  });

  it('should switch to hours and minutes past an hour', () => {
    expect(formatElapsed(3_600_000)).toBe('1h 00m');
    expect(formatElapsed(3_840_000)).toBe('1h 04m');
  });

  /** Clock skew, or a `startedAt` from a snapshot taken a tick ahead — neither should render "-3s". */
  it('should floor a negative elapsed at zero', () => {
    expect(formatElapsed(-3000)).toBe('0s');
  });
});
