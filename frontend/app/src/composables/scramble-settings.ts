import type { ComputedRef, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { generateRandomScrambleMultiplier } from '@/utils/session';

interface UseScrambleSettingReturn {
  scrambleData: Ref<boolean>;
  scrambleMultiplier: Ref<string>;
  enabled: ComputedRef<boolean>;
  multiplier: ComputedRef<number | undefined>;
  handleMultiplierUpdate: (value: string) => void;
  randomMultiplier: () => string;
}

export function useScrambleSetting(): UseScrambleSettingReturn {
  const frontendStore = useFrontendSettingsStore();
  const { scrambleData: enabled, scrambleMultiplier: multiplier } = storeToRefs(frontendStore);

  const scrambleData = ref<boolean>(false);
  const scrambleMultiplier = ref<string>('0');
  const isUpdating = ref<boolean>(false);

  // Debounced backend update
  const debouncedBackendUpdate = useDebounceFn(async (value: number) => {
    await frontendStore.updateSetting({ scrambleMultiplier: value });
  }, 500);

  function randomMultiplier(): string {
    const value = generateRandomScrambleMultiplier().toString();
    set(scrambleMultiplier, value);
    return value;
  }

  function handleMultiplierUpdate(value: string): void {
    set(isUpdating, true);
    set(scrambleMultiplier, value);

    const numValue = Number(value);

    // Update store immediately for UI
    frontendStore.update({
      ...frontendStore.$state.settings,
      scrambleMultiplier: numValue,
    });

    // Debounce backend update
    startPromise(debouncedBackendUpdate(numValue));

    setTimeout(() => set(isUpdating, false), 600);
  }

  function initializeData(): void {
    set(scrambleData, get(enabled));
    if (!get(isUpdating)) {
      set(scrambleMultiplier, (get(multiplier) ?? generateRandomScrambleMultiplier()).toString());
    }
  }

  onMounted(initializeData);

  watchImmediate([enabled, multiplier], () => {
    if (!get(isUpdating)) {
      initializeData();
    }
  });

  return {
    enabled,
    handleMultiplierUpdate,
    multiplier,
    randomMultiplier,
    scrambleData,
    scrambleMultiplier,
  };
}
