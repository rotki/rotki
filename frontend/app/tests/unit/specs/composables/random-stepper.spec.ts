import type * as Vue from 'vue';
import { useRandomStepper } from '@/composables/random-stepper';
import { beforeAll, describe, expect, it, vi } from 'vitest';

describe('composables::random-stepper', () => {
  beforeAll(() => {
    const pinia = createPinia();
    vi.useFakeTimers();
    setActivePinia(pinia);

    vi.mock('vue', async () => {
      const mod = await vi.importActual<typeof Vue>('vue');

      return {
        ...mod,
        onMounted: vi.fn().mockImplementation((fn: () => void) => fn()),
      };
    });
  });

  it('should not randomise when it is a single message', () => {
    const { step, steps } = useRandomStepper(1, 1000);

    expect(get(step)).toEqual(1);
    expect(get(steps)).toEqual(1);

    vi.advanceTimersByTime(1000);

    expect(get(step)).toEqual(1);
    expect(get(steps)).toEqual(1);
  });

  it('should randomise when there are multiple messages', () => {
    const { step, steps } = useRandomStepper(5, 1000);

    expect(get(step)).toEqual(1);
    expect(get(steps)).toEqual(5);

    vi.advanceTimersByTime(1000);

    let lastStep = get(step);
    expect(get(step)).not.toEqual(1);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
    lastStep = get(step);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
  });

  it('should not randomise when timer is paused', () => {
    const { step, steps, onPause, onResume } = useRandomStepper(5, 1000);

    expect(get(step)).toEqual(1);
    expect(get(steps)).toEqual(5);

    onPause();
    vi.advanceTimersByTime(1000);

    expect(get(step)).toEqual(1);

    onResume();
    vi.advanceTimersByTime(1000);

    let lastStep = get(step);
    expect(get(step)).not.toEqual(1);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
    lastStep = get(step);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
  });

  it('should reset random timer when user navigates', async () => {
    const { step, steps, onNavigate } = useRandomStepper(5, 1000);

    expect(get(step)).toEqual(1);
    expect(get(steps)).toEqual(5);

    vi.advanceTimersByTime(900);
    await onNavigate(2);

    expect(get(step)).toEqual(2);

    vi.advanceTimersByTime(100);

    expect(get(step)).toEqual(2);

    await nextTick();

    vi.advanceTimersByTime(1100);
    expect(get(step)).not.toEqual(2);

    await onNavigate(2);
    expect(get(step)).toEqual(2);
  });
});
