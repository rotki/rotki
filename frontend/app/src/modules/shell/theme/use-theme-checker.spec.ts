import { Theme } from '@rotki/common';
import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref } from 'vue';

const mockSelectedTheme = ref<Theme>(Theme.AUTO);
const mockLogged = ref<boolean>(false);
const mockUpdateDarkMode = vi.fn();

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockSelectedTheme),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: vi.fn(() => ({ logged: mockLogged })),
}));

vi.mock('@/modules/shell/theme/use-dark-mode', () => ({
  useDarkMode: vi.fn(() => ({ updateDarkMode: mockUpdateDarkMode })),
}));

interface MockMediaQueryList {
  matches: boolean;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
}

let mediaQueryList: MockMediaQueryList;

function createMediaQueryList(matches: boolean): MockMediaQueryList {
  return {
    addEventListener: vi.fn(),
    matches,
    removeEventListener: vi.fn(),
  };
}

async function mountChecker(): Promise<ReturnType<typeof mount>> {
  vi.resetModules();
  const { useThemeChecker } = await import('@/modules/shell/theme/use-theme-checker');
  const component = defineComponent({
    setup() {
      useThemeChecker();
      return {};
    },
    template: '<div />',
  });
  return mount(component);
}

describe('useThemeChecker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mediaQueryList = createMediaQueryList(false);
    vi.stubGlobal('matchMedia', vi.fn(() => mediaQueryList));
    set(mockSelectedTheme, Theme.AUTO);
    set(mockLogged, false);
  });

  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it('should enable dark mode on mount when logged in with the dark theme selected', async () => {
    set(mockLogged, true);
    set(mockSelectedTheme, Theme.DARK);
    await mountChecker();
    expect(mockUpdateDarkMode).toHaveBeenLastCalledWith(true);
  });

  it('should disable dark mode on mount when logged in with the light theme selected', async () => {
    set(mockLogged, true);
    set(mockSelectedTheme, Theme.LIGHT);
    await mountChecker();
    expect(mockUpdateDarkMode).toHaveBeenLastCalledWith(false);
  });

  it('should use the stored theme when not logged in', async () => {
    const stored: Ref<Theme> = useLocalStorage<Theme>('rotki.selected_theme', Theme.AUTO);
    set(stored, Theme.DARK);
    await mountChecker();
    expect(mockUpdateDarkMode).toHaveBeenLastCalledWith(true);
  });

  it('should follow the preferred color scheme when the theme is auto', async () => {
    set(mockLogged, true);
    set(mockSelectedTheme, Theme.AUTO);
    mediaQueryList = createMediaQueryList(true);
    vi.stubGlobal('matchMedia', vi.fn(() => mediaQueryList));
    await mountChecker();
    expect(mockUpdateDarkMode).toHaveBeenLastCalledWith(true);
  });

  it('should register a media query change listener on mount', async () => {
    await mountChecker();
    expect(mediaQueryList.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));
  });

  it('should re-evaluate the theme when the media query changes', async () => {
    set(mockLogged, true);
    set(mockSelectedTheme, Theme.AUTO);
    await mountChecker();
    mockUpdateDarkMode.mockClear();

    const handler = mediaQueryList.addEventListener.mock.calls[0][1];
    handler({ matches: true });
    await nextTick();

    expect(mockUpdateDarkMode).toHaveBeenLastCalledWith(true);
  });

  it('should persist the selected theme to local storage when logged in', async () => {
    set(mockLogged, true);
    set(mockSelectedTheme, Theme.LIGHT);
    await mountChecker();

    set(mockSelectedTheme, Theme.DARK);
    await nextTick();

    const stored = useLocalStorage<Theme>('rotki.selected_theme', Theme.AUTO);
    expect(get(stored)).toBe(Theme.DARK);
  });

  it('should remove the media query listener on unmount', async () => {
    const wrapper = await mountChecker();
    wrapper.unmount();
    expect(mediaQueryList.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function));
  });
});
