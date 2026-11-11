import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useStepTransition } from '@/modules/auth/create-account/use-step-transition';

describe('useStepTransition', () => {
  it('should slide forward before any move', () => {
    const { classes } = useStepTransition(ref<number>(0));

    expect(get(classes).enterFromClass).toContain('translate-x-6');
    expect(get(classes).enterFromClass).not.toContain('-translate-x-6');
  });

  it('should bring the next step in from the right', () => {
    const position = ref<number>(1);
    const { classes } = useStepTransition(position);

    set(position, 2);

    expect(get(classes)).toStrictEqual({
      enterFromClass: 'opacity-0 translate-x-6',
      leaveToClass: 'opacity-0 -translate-x-6',
    });
  });

  it('should bring the previous step in from the left', () => {
    const position = ref<number>(2);
    const { classes } = useStepTransition(position);

    set(position, 1);

    expect(get(classes)).toStrictEqual({
      enterFromClass: 'opacity-0 -translate-x-6',
      leaveToClass: 'opacity-0 translate-x-6',
    });
  });

  /** The leaving screen reads its classes in the same render, so a deferred update is too late. */
  it('should settle the direction as soon as the position changes', () => {
    const position = ref<number>(3);
    const { classes } = useStepTransition(position);

    set(position, 0);

    expect(get(classes).leaveToClass).toBe('opacity-0 translate-x-6');
  });
});
