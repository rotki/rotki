import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMarqueeAnimation } from '@/modules/shell/layout/use-marquee-animation';

function makeMarquee(scrollWidth: number, clientWidth: number, withChild = true): {
  wrapper: HTMLElement;
  inner: HTMLElement | undefined;
  animation: Animation;
} {
  const wrapper = document.createElement('div');
  Object.defineProperty(wrapper, 'clientWidth', { configurable: true, value: clientWidth });

  const animation = createMock<Animation>({ cancel: vi.fn() });
  let inner: HTMLElement | undefined;
  if (withChild) {
    inner = document.createElement('div');
    Object.defineProperty(inner, 'scrollWidth', { configurable: true, value: scrollWidth });
    inner.animate = vi.fn(() => animation);
    wrapper.appendChild(inner);
  }

  return { animation, inner, wrapper };
}

describe('useMarqueeAnimation', () => {
  let marquee: ReturnType<typeof useMarqueeAnimation>;

  // Dispatch a real event so `currentTarget` is populated by the DOM (it is a
  // read-only accessor that can only be set during actual event dispatch).
  function fireEnter(wrapper: HTMLElement): void {
    wrapper.addEventListener('mouseenter', marquee.onMarqueeEnter, { once: true });
    wrapper.dispatchEvent(new MouseEvent('mouseenter'));
  }

  function fireLeave(wrapper: HTMLElement): void {
    wrapper.addEventListener('mouseleave', marquee.onMarqueeLeave, { once: true });
    wrapper.dispatchEvent(new MouseEvent('mouseleave'));
  }

  beforeEach(() => {
    marquee = useMarqueeAnimation();
  });

  describe('onMarqueeEnter', () => {
    it('should animate the inner element when it overflows', () => {
      const { inner, wrapper } = makeMarquee(300, 200);
      fireEnter(wrapper);

      expect(inner?.animate).toHaveBeenCalledOnce();
    });

    it('should run the animation forever with the computed duration', () => {
      const { inner, wrapper } = makeMarquee(300, 200);
      fireEnter(wrapper);

      // distance 100 → scrollDuration max(1000, 1500)=1500, +2*500 pause = 2500
      const animateMock = vi.mocked(inner!.animate);
      expect(animateMock.mock.calls[0][1]).toMatchObject({ duration: 2500, iterations: Infinity });
    });

    it('should not animate when the inner element does not overflow', () => {
      const { inner, wrapper } = makeMarquee(150, 200);
      fireEnter(wrapper);

      expect(inner?.animate).not.toHaveBeenCalled();
    });

    it('should do nothing when there is no inner element', () => {
      const { wrapper } = makeMarquee(0, 200, false);

      expect(() => fireEnter(wrapper)).not.toThrow();
    });
  });

  describe('onMarqueeLeave', () => {
    it('should cancel a running animation', () => {
      const { animation, wrapper } = makeMarquee(300, 200);
      fireEnter(wrapper);
      fireLeave(wrapper);

      expect(animation.cancel).toHaveBeenCalledOnce();
    });

    it('should do nothing when there is no animation for the element', () => {
      const { animation, wrapper } = makeMarquee(300, 200);
      fireLeave(wrapper);

      expect(animation.cancel).not.toHaveBeenCalled();
    });

    it('should do nothing when there is no inner element', () => {
      const { wrapper } = makeMarquee(0, 200, false);

      expect(() => fireLeave(wrapper)).not.toThrow();
    });
  });
});
