import type { Ref } from 'vue';

interface UseRandomStepperReturn {
  onNavigate: (newStep: number) => Promise<void>;
  onPause: () => void;
  onResume: () => void;
  step: Ref<number>;
  steps: number;
}

export function useRandomStepper(steps: number, interval: number = 10000): UseRandomStepperReturn {
  const step = ref(1);

  function setRandomStep(): void {
    let newStep = get(step);
    if (steps > 1) {
      while (newStep === get(step)) newStep = Math.ceil(Math.random() * steps);
    }

    set(step, newStep);
  }

  const { pause, resume } = useIntervalFn(setRandomStep, interval);

  async function onNavigate(newStep: number): Promise<void> {
    pause();
    set(step, newStep);
    await nextTick(resume);
  }

  onMounted(() => {
    if (steps <= 1)
      pause();
  });

  return {
    onNavigate,
    onPause: pause,
    onResume: resume,
    step,
    steps,
  };
}
