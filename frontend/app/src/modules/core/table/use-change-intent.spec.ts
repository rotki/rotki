import { get } from '@vueuse/shared';
import { describe, expect, it } from 'vitest';
import { useChangeIntent } from '@/modules/core/table/use-change-intent';

describe('useChangeIntent', () => {
  it('should start with no pending url source and a programmatic intent', () => {
    const { pendingIntent, pendingUrlSource } = useChangeIntent();
    expect(get(pendingIntent)).toBe('programmatic');
    expect(get(pendingUrlSource)).toBeUndefined();
  });

  it('should raise the intent for a real source', () => {
    const { markSource, pendingIntent } = useChangeIntent();
    markSource('route');
    expect(get(pendingIntent)).toBe('route');
    markSource('restore');
    expect(get(pendingIntent)).toBe('restore');
    markSource('self');
    expect(get(pendingIntent)).toBe('self');
  });

  it('should never lower a pending intent back to programmatic', () => {
    const { markSource, pendingIntent } = useChangeIntent();
    markSource('user');
    expect(get(pendingIntent)).toBe('user');
    // an internal reset must not swallow the user's earned url write
    markSource('programmatic');
    expect(get(pendingIntent)).toBe('user');
  });

  it('should keep programmatic when nothing has raised the intent', () => {
    const { markSource, pendingIntent } = useChangeIntent();
    markSource('programmatic');
    expect(get(pendingIntent)).toBe('programmatic');
  });

  it('should attribute the next change to the user via markUserIntent', () => {
    const { markUserIntent, pendingIntent } = useChangeIntent();
    markUserIntent();
    expect(get(pendingIntent)).toBe('user');
  });
});
