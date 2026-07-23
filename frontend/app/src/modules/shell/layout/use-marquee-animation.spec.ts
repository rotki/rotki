import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { useMarqueeAnimation } from '@/modules/shell/layout/use-marquee-animation';

function makeMarquee(scrollWidth: number, clientWidth: number, withChild = true): {
  wrapper: HTMLElement;
  inner: HTMLElement | undefined;
  animation: Animation;
  animateSpy: Mock;
  cancelSpy: Mock;
} {
  const wrapper = document.createElement('div');
  Object.defineProperty(wrapper, 'clientWidth', { configurable: true, value: clientWidth });

  const cancelSpy = vi.fn();
  const animation = createMock<Animation>({ cancel: cancelSpy });
  const animateSpy = vi.fn(() => animation);
  let inner: HTMLElement | undefined;
  if (withChild) {
    inner = document.createElement('div');
    Object.defineProperty(inner, 'scrollWidth', { configurable: true, value: scrollWidth });
    inner.animate = animateSpy;
    wrapper.appendChild(inner);
  }

  return { animateSpy, animation, cancelSpy, inner, wrapper };
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
      const { animateSpy, wrapper } = makeMarquee(300, 200);
      fireEnter(wrapper);

      expect(animateSpy).toHaveBeenCalledOnce();
    });

    it('should run the animation forever with the computed duration', () => {
      const { animateSpy, wrapper } = makeMarquee(300, 200);
      fireEnter(wrapper);

      // distance 100 → scrollDuration max(1000, 1500)=1500, +2*500 pause = 2500
      expect(animateSpy.mock.calls[0][1]).toMatchObject({ duration: 2500, iterations: Infinity });
    });

    it('should not animate when the inner element does not overflow', () => {
      const { animateSpy, wrapper } = makeMarquee(150, 200);
      fireEnter(wrapper);

      expect(animateSpy).not.toHaveBeenCalled();
    });

    it('should do nothing when there is no inner element', () => {
      const { wrapper } = makeMarquee(0, 200, false);

      expect(() => fireEnter(wrapper)).not.toThrow();
    });
  });

  describe('onMarqueeLeave', () => {
    it('should cancel a running animation', () => {
      const { cancelSpy, wrapper } = makeMarquee(300, 200);
      fireEnter(wrapper);
      fireLeave(wrapper);

      expect(cancelSpy).toHaveBeenCalledOnce();
    });

    it('should do nothing when there is no animation for the element', () => {
      const { cancelSpy, wrapper } = makeMarquee(300, 200);
      fireLeave(wrapper);

      expect(cancelSpy).not.toHaveBeenCalled();
    });

    it('should do nothing when there is no inner element', () => {
      const { wrapper } = makeMarquee(0, 200, false);

      expect(() => fireLeave(wrapper)).not.toThrow();
    });
  });
});
