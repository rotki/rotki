import type { VueWrapper } from '@vue/test-utils';
import type { StakingLocation } from '@/pages/staking/staking-pages';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useStakingPage } from './use-staking-page';

const LAST_LOCATION_KEY = 'rotki.staking.last_location';

const pushMock = vi.hoisted(() => vi.fn(async (): Promise<void> => {}));

vi.mock('vue-router', () => ({
  useRouter: (): { push: typeof pushMock } => ({ push: pushMock }),
}));

// The real map pulls in four staking pages; only the identity of each entry matters here.
vi.mock('@/pages/staking/staking-pages', () => ({
  stakingPages: {
    'eth2': { name: 'Eth2Page' },
    'kraken': { name: 'KrakenPage' },
    'lido-csm': { name: 'LidoCsmPage' },
    'liquity': { name: 'LiquityPage' },
  },
}));

vi.mock('@/modules/core/common/file/file', () => ({
  getPublicProtocolImagePath: (file: string): string => `/images/protocols/${file}`,
}));

describe('pages/staking/useStakingPage', () => {
  // The composable registers an onMounted hook that can navigate, so a leftover harness would
  // push during a later test.
  const mounted: VueWrapper[] = [];

  function setup(location: StakingLocation | ''): ReturnType<typeof useStakingPage> {
    const { result, wrapper } = withSetup(() => useStakingPage(() => location));
    mounted.push(wrapper);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    while (mounted.length > 0)
      mounted.pop()?.unmount();
  });

  describe('with a location in the route', () => {
    it('should resolve the page for that location', async () => {
      const { page } = setup('kraken');
      await flushPromises();

      expect(get(page)).toEqual({ name: 'KrakenPage' });
    });

    it('should remember it as the last location', async () => {
      setup('liquity');
      await flushPromises();

      expect(localStorage.getItem(LAST_LOCATION_KEY)).toContain('liquity');
    });

    it('should overwrite a different remembered location', async () => {
      localStorage.setItem(LAST_LOCATION_KEY, 'kraken');

      setup('eth2');
      await flushPromises();

      expect(localStorage.getItem(LAST_LOCATION_KEY)).toContain('eth2');
    });
  });

  describe('with no location in the route', () => {
    it('should resolve no page, so the picker shows', async () => {
      const { page } = setup('');
      await flushPromises();

      expect(get(page)).toBeNull();
    });

    it('should stay put when nothing was remembered', async () => {
      const { page } = setup('');
      await flushPromises();

      expect(pushMock).not.toHaveBeenCalled();
      expect(get(page)).toBeNull();
    });

    it('should reopen the remembered location', async () => {
      localStorage.setItem(LAST_LOCATION_KEY, 'lido-csm');

      setup('');
      await flushPromises();

      expect(pushMock).toHaveBeenCalledWith({
        name: '/staking/[[location]]',
        params: { location: 'lido-csm' },
      });
    });

    it('should not record anything new while redirecting', async () => {
      localStorage.setItem(LAST_LOCATION_KEY, 'kraken');

      setup('');
      await flushPromises();

      expect(localStorage.getItem(LAST_LOCATION_KEY)).toContain('kraken');
    });
  });

  describe('choosing a location from the dropdown', () => {
    it('should navigate to the chosen one and remember it', async () => {
      const { modelLocation } = setup('');
      await flushPromises();

      set(modelLocation, 'liquity');
      await flushPromises();

      expect(pushMock).toHaveBeenCalledWith({
        name: '/staking/[[location]]',
        params: { location: 'liquity' },
      });
      expect(localStorage.getItem(LAST_LOCATION_KEY)).toContain('liquity');
    });

    it('should clear the remembered location and navigate nowhere when the choice is cleared', async () => {
      localStorage.setItem(LAST_LOCATION_KEY, 'kraken');
      const { modelLocation } = setup('kraken');
      await flushPromises();
      pushMock.mockClear();

      set(modelLocation, undefined);
      await flushPromises();

      expect(pushMock).not.toHaveBeenCalled();
    });

    it('should read the route param back out, not what was written', async () => {
      const { modelLocation } = setup('kraken');
      await flushPromises();

      set(modelLocation, 'eth2');
      await flushPromises();

      // The prop is the source of truth; the write only navigates, and the real route change is
      // what swaps the page.
      expect(get(modelLocation)).toBe('kraken');
    });
  });

  it('should offer the four staking locations with their images', async () => {
    const { staking } = setup('');
    await flushPromises();

    expect(get(staking).map(item => item.id)).toEqual(['eth2', 'liquity', 'kraken', 'lido-csm']);
    expect(get(staking)[0].image).toBe('/images/protocols/ethereum.svg');
  });

  it('should build a redirect link for a location', async () => {
    const { getRedirectLink } = setup('');
    await flushPromises();

    expect(getRedirectLink('kraken')).toEqual({
      name: '/staking/[[location]]',
      params: { location: 'kraken' },
    });
  });
});
