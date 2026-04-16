interface UseMarqueeAnimationReturn {
  onMarqueeEnter: (event: MouseEvent) => void;
  onMarqueeLeave: (event: MouseEvent) => void;
}

export function useMarqueeAnimation(): UseMarqueeAnimationReturn {
  const animations = new WeakMap<HTMLElement, Animation>();

  function onMarqueeEnter(event: MouseEvent): void {
    const wrapper = event.currentTarget as HTMLElement;
    const inner = wrapper.firstElementChild as HTMLElement | null;
    if (!inner)
      return;

    const distance: number = inner.scrollWidth - wrapper.clientWidth;
    if (distance <= 0)
      return;

    const scrollDuration: number = Math.max(1000, distance * 15);
    const pauseDuration: number = 500;
    const totalDuration: number = scrollDuration + 2 * pauseDuration;
    const pauseOffset: number = pauseDuration / totalDuration;

    const animation: Animation = inner.animate(
      [
        { transform: 'translateX(0)', offset: 0 },
        { transform: 'translateX(0)', offset: pauseOffset },
        { transform: `translateX(-${distance}px)`, offset: 1 - pauseOffset },
        { transform: `translateX(-${distance}px)`, offset: 1 },
      ],
      { duration: totalDuration, iterations: Infinity },
    );
    animations.set(inner, animation);
  }

  function onMarqueeLeave(event: MouseEvent): void {
    const wrapper = event.currentTarget as HTMLElement;
    const inner = wrapper.firstElementChild as HTMLElement | null;
    if (!inner)
      return;

    const animation: Animation | undefined = animations.get(inner);
    if (animation) {
      animation.cancel();
      animations.delete(inner);
    }
  }

  return {
    onMarqueeEnter,
    onMarqueeLeave,
  };
}
