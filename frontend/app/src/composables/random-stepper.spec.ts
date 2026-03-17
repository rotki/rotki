import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRandomStepper } from '@/composables/random-stepper';

describe('useRandomStepper', () => {
  beforeAll(() => {
    vi.useFakeTimers();
  });

  function mountStepper(steps: number, interval: number = 1000): { wrapper: VueWrapper; result: ReturnType<typeof useRandomStepper> } {
    let result!: ReturnType<typeof useRandomStepper>;
    const wrapper = mount(defineComponent({
      setup() {
        result = useRandomStepper(steps, interval);
        return {};
      },
      render: () => null,
    }));
    return { wrapper, result };
  }

  let wrapper: VueWrapper;

  beforeEach(() => {
    wrapper?.unmount();
  });

  it('should not randomise when it is a single message', () => {
    const { wrapper: w, result: { step, steps } } = mountStepper(1);
    wrapper = w;

    expect(get(step)).toBe(1);
    expect(steps).toBe(1);

    vi.advanceTimersByTime(1000);

    expect(get(step)).toBe(1);
    expect(steps).toBe(1);
  });

  it('should randomise when there are multiple messages', () => {
    const { wrapper: w, result: { step, steps } } = mountStepper(5);
    wrapper = w;

    expect(get(step)).toBe(1);
    expect(steps).toBe(5);

    vi.advanceTimersByTime(1000);

    let lastStep = get(step);
    expect(get(step)).not.toBe(1);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
    lastStep = get(step);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
  });

  it('should not randomise when timer is paused', () => {
    const { wrapper: w, result: { step, steps, onPause, onResume } } = mountStepper(5);
    wrapper = w;

    expect(get(step)).toBe(1);
    expect(steps).toBe(5);

    onPause();
    vi.advanceTimersByTime(1000);

    expect(get(step)).toBe(1);

    onResume();
    vi.advanceTimersByTime(1000);

    let lastStep = get(step);
    expect(get(step)).not.toBe(1);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
    lastStep = get(step);

    vi.advanceTimersByTime(1000);

    expect(get(step)).not.toEqual(lastStep);
  });

  it('should reset random timer when user navigates', async () => {
    const { wrapper: w, result: { step, steps, onNavigate } } = mountStepper(5);
    wrapper = w;

    expect(get(step)).toBe(1);
    expect(steps).toBe(5);

    vi.advanceTimersByTime(900);
    await onNavigate(2);

    expect(get(step)).toBe(2);

    vi.advanceTimersByTime(100);

    expect(get(step)).toBe(2);

    await nextTick();

    vi.advanceTimersByTime(1100);
    expect(get(step)).not.toBe(2);

    await onNavigate(2);
    expect(get(step)).toBe(2);
  });
});
