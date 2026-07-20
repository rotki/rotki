import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import { useScrambleSetting } from './use-scramble-settings';

type ScrambleApi = ReturnType<typeof useScrambleSetting>;

const scrambleData = ref<boolean>(false);
const scrambleMultiplier = ref<number | undefined>(undefined);
const applyFrontendSettingLocal = vi.fn();
const updateFrontendSetting = vi.fn();
const generateRandomScrambleMultiplier = vi.fn(() => 5);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => Reflect.get({ scrambleData, scrambleMultiplier }, key) ?? ref(undefined)),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ applyFrontendSettingLocal, updateFrontendSetting }),
}));

vi.mock('@/modules/session/session-utils', () => ({
  generateRandomScrambleMultiplier: (): number => generateRandomScrambleMultiplier(),
}));

function mountComposable(): { api: ScrambleApi; unmount: () => void } {
  let api!: ScrambleApi;
  const wrapper = mount(defineComponent({
    setup(): () => VNode {
      api = useScrambleSetting();
      return () => h('div');
    },
  }));
  return { api, unmount: () => wrapper.unmount() };
}

describe('useScrambleSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    set(scrambleData, false);
    set(scrambleMultiplier, undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should initialize local state from the store', () => {
    set(scrambleData, true);
    set(scrambleMultiplier, 7);
    const { api, unmount } = mountComposable();
    expect(get(api.modelScrambleData)).toBe(true);
    expect(get(api.modelScrambleMultiplier)).toBe('7');
    unmount();
  });

  it('should fall back to a random multiplier when none is stored', () => {
    const { api, unmount } = mountComposable();
    expect(get(api.modelScrambleMultiplier)).toBe('5');
    unmount();
  });

  it('should generate and store a random multiplier on demand', () => {
    const { api, unmount } = mountComposable();
    const value = api.randomMultiplier();
    expect(value).toBe('5');
    expect(get(api.modelScrambleMultiplier)).toBe('5');
    unmount();
  });

  it('should apply the setting locally immediately and to the backend after debounce', async () => {
    const { api, unmount } = mountComposable();
    api.handleMultiplierUpdate('3');
    expect(get(api.modelScrambleMultiplier)).toBe('3');
    expect(applyFrontendSettingLocal).toHaveBeenCalledWith({ scrambleMultiplier: 3 });
    expect(updateFrontendSetting).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(500);
    expect(updateFrontendSetting).toHaveBeenCalledWith({ scrambleMultiplier: 3 });
    unmount();
  });
});
