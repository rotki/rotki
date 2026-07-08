import type { Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { generateRandomScrambleMultiplier } from '@/modules/session/session-utils';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseScrambleSettingReturn {
  scrambleData: Ref<boolean>;
  scrambleMultiplier: Ref<string>;
  enabled: Readonly<Ref<boolean>>;
  multiplier: Readonly<Ref<number | undefined>>;
  handleMultiplierUpdate: (value: string) => void;
  randomMultiplier: () => string;
}

export function useScrambleSetting(): UseScrambleSettingReturn {
  const scrambleData = shallowRef<boolean>(false);
  const scrambleMultiplier = shallowRef<string>('0');
  const isUpdating = shallowRef<boolean>(false);
  let timeoutId: number;

  const enabled = useSetting('scrambleData');
  const multiplier = useSetting('scrambleMultiplier');
  const { applyFrontendSettingLocal, updateFrontendSetting } = useSettingsOperations();

  // Debounced backend update
  const debouncedBackendUpdate = useDebounceFn(async (value: number) => {
    await updateFrontendSetting({ scrambleMultiplier: value });
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

    applyFrontendSettingLocal({ scrambleMultiplier: numValue });

    // Debounce backend update
    startPromise(debouncedBackendUpdate(numValue));
    timeoutId = setTimeout(set, 600, isUpdating, false);
  }

  function initializeData(): void {
    set(scrambleData, get(enabled));
    if (!get(isUpdating)) {
      set(scrambleMultiplier, (get(multiplier) ?? generateRandomScrambleMultiplier()).toString());
    }
  }

  onScopeDispose(() => {
    if (timeoutId)
      clearTimeout(timeoutId);
  });

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
