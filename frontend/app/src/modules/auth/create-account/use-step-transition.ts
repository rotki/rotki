import type { ComputedRef, MaybeRefOrGetter } from 'vue';

interface StepTransitionClasses {
  enterFromClass: string;
  leaveToClass: string;
}

interface UseStepTransitionReturn {
  /** The `<Transition>` classes for the move under way: forward slides left, back slides right. */
  classes: ComputedRef<StepTransitionClasses>;
}

const FORWARD: StepTransitionClasses = {
  enterFromClass: 'opacity-0 translate-x-6',
  leaveToClass: 'opacity-0 -translate-x-6',
};

const BACK: StepTransitionClasses = {
  enterFromClass: 'opacity-0 -translate-x-6',
  leaveToClass: 'opacity-0 translate-x-6',
};

/**
 * Slides the wizard's screens in the direction the user is moving.
 *
 * @remarks
 * The direction is settled synchronously when the position changes, because the leaving screen reads
 * its classes in the same render that swaps it out: a later flush would animate the old direction.
 *
 * @param position - where the user is in the flow, 0 for the path choice and the 1-based step after
 */
export function useStepTransition(position: MaybeRefOrGetter<number>): UseStepTransitionReturn {
  const forward = shallowRef<boolean>(true);

  watch(() => toValue(position), (next, previous) => {
    set(forward, next >= previous);
  }, { flush: 'sync' });

  const classes = computed<StepTransitionClasses>(() => (get(forward) ? FORWARD : BACK));

  return { classes };
}
