import { describe, expect, it } from 'vitest';
import { getEventDirectionColor, getEventDirectionIcon, getEventDirectionTextClass } from './event-direction';

describe('event-direction', () => {
  it('should map incoming to a down arrow tinted success/green', () => {
    expect(getEventDirectionIcon('in')).toBe('lu-arrow-down');
    expect(getEventDirectionColor('in')).toBe('success');
    expect(getEventDirectionTextClass('in')).toBe('text-rui-success');
  });

  it('should map outgoing to an up arrow tinted error/red', () => {
    expect(getEventDirectionIcon('out')).toBe('lu-arrow-up');
    expect(getEventDirectionColor('out')).toBe('error');
    expect(getEventDirectionTextClass('out')).toBe('text-rui-error');
  });

  it('should map neutral to a dash tinted secondary/grey', () => {
    expect(getEventDirectionIcon('neutral')).toBe('lu-minus');
    expect(getEventDirectionColor('neutral')).toBe('secondary');
    expect(getEventDirectionTextClass('neutral')).toBe('text-rui-text-secondary');
  });
});
