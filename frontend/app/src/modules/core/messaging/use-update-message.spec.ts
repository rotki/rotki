import { externalLinks } from '@shared/external-links';
import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref } from 'vue';

const mockAppVersion = ref<string>('1.0.0');

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: (): { appVersion: Ref<string> } => ({ appVersion: mockAppVersion }),
}));

const LAST_VERSION_KEY = 'rotki.last_version';

const wrappers: ReturnType<typeof mount>[] = [];

async function mountUpdateMessage(): Promise<{
  wrapper: ReturnType<typeof mount>;
  result: Awaited<ReturnType<typeof import('@/modules/core/messaging/use-update-message')['useUpdateMessage']>>;
}> {
  vi.resetModules();
  const { useUpdateMessage } = await import('@/modules/core/messaging/use-update-message');
  let result!: ReturnType<typeof useUpdateMessage>;
  const component = defineComponent({
    setup() {
      result = useUpdateMessage();
      return {};
    },
    template: '<div />',
  });
  const wrapper = mount(component);
  wrappers.push(wrapper);
  return { result, wrapper };
}

describe('useUpdateMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    set(mockAppVersion, '1.0.0');
  });

  afterEach(() => {
    // Unmount every mounted wrapper so the createSharedComposable scope disposes and its
    // watch(appVersion) detaches from the shared mockAppVersion ref. Otherwise a leaked
    // watcher from a prior test fires on the next beforeEach set() and writes localStorage
    // after it was cleared, breaking within-file test-order isolation.
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
    localStorage.clear();
  });

  it('should show release notes on first launch of a new version', async () => {
    const { result } = await mountUpdateMessage();
    expect(get(result.showReleaseNotes)).toBe(true);
    expect(localStorage.getItem(LAST_VERSION_KEY)).toBe('1.0.0');
  });

  it('should not show release notes when the last used version matches', async () => {
    localStorage.setItem(LAST_VERSION_KEY, '1.0.0');
    const { result } = await mountUpdateMessage();
    expect(get(result.showReleaseNotes)).toBe(false);
  });

  it('should show release notes when the version changed since last use', async () => {
    localStorage.setItem(LAST_VERSION_KEY, '0.9.0');
    const { result } = await mountUpdateMessage();
    expect(get(result.showReleaseNotes)).toBe(true);
  });

  it('should skip release notes for a dev version', async () => {
    set(mockAppVersion, '1.0.0-dev');
    const { result } = await mountUpdateMessage();
    expect(get(result.showReleaseNotes)).toBe(false);
    expect(localStorage.getItem(LAST_VERSION_KEY)).toBeNull();
  });

  it('should skip release notes when the version is empty', async () => {
    set(mockAppVersion, '');
    const { result } = await mountUpdateMessage();
    expect(get(result.showReleaseNotes)).toBe(false);
  });

  it('should build the release link for the current version', async () => {
    const { result } = await mountUpdateMessage();
    expect(get(result.link)).toBe(externalLinks.releasesVersion.replace('$version', '1.0.0'));
  });

  it('should expose the current version', async () => {
    set(mockAppVersion, '2.3.4');
    const { result } = await mountUpdateMessage();
    expect(get(result.version)).toBe('2.3.4');
  });
});
