import type { Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { generateRandomScrambleMultiplier } from '@/modules/session/session-utils';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseScrambleSettingReturn {
  modelScrambleData: Ref<boolean>;
  modelScrambleMultiplier: Ref<string>;
  enabled: Readonly<Ref<boolean>>;
  multiplier: Readonly<Ref<number | undefined>>;
  handleMultiplierUpdate: (value: string) => void;
  randomMultiplier: () => string;
}

export function useScrambleSetting(): UseScrambleSettingReturn {
  const modelScrambleData = shallowRef<boolean>(false);
  const modelScrambleMultiplier = shallowRef<string>('0');
  const isUpdating = shallowRef<boolean>(false);
  let timeoutId: number;

  const enabled = useSetting('scrambleData');
  const multiplier = useSetting('scrambleMultiplier');
  const { applyFrontendSettingLocal, updateFrontendSetting } = useSettingsOperations();

  const debouncedBackendUpdate = useDebounceFn(async (value: number) => {
    await updateFrontendSetting({ scrambleMultiplier: value });
  }, 500);

  function randomMultiplier(): string {
    const value = generateRandomScrambleMultiplier().toString();
    set(modelScrambleMultiplier, value);
    return value;
  }

  function handleMultiplierUpdate(value: string): void {
    set(isUpdating, true);
    set(modelScrambleMultiplier, value);

    const numValue = Number(value);

    applyFrontendSettingLocal({ scrambleMultiplier: numValue });

    startPromise(debouncedBackendUpdate(numValue));
    timeoutId = setTimeout(set, 600, isUpdating, false);
  }

  function initializeData(): void {
    set(modelScrambleData, get(enabled));
    if (!get(isUpdating)) {
      set(modelScrambleMultiplier, (get(multiplier) ?? generateRandomScrambleMultiplier()).toString());
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
    modelScrambleData,
    modelScrambleMultiplier,
  };
}
