export function useRandomStepper(steps: number, interval: number = 10000) {
  const step = ref(1);

  function setRandomStep() {
    let newStep = get(step);
    if (steps > 1)
      while (newStep === get(step)) newStep = Math.ceil(Math.random() * steps);

    set(step, newStep);
  }

  const { pause, resume } = useIntervalFn(setRandomStep, interval);

  async function onNavigate(newStep: number) {
    pause();
    set(step, newStep);
    await nextTick(resume);
  }

  onMounted(() => {
    if (steps <= 1)
      pause();
  });

  return {
    step,
    steps,
    onNavigate,
    onPause: pause,
    onResume: resume,
  };
}
