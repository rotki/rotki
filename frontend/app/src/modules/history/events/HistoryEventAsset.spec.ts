import type { SmallValueSubject } from '@/modules/history/events/use-small-value-events';
import { createOnlineHistoryEvent } from '@test/utils/history-events';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';

/** The assets the mocked classifier calls small, so a test decides what the threshold catches. */
const smallAssets = vi.hoisted(() => new Set<string>());

vi.mock('@/modules/history/events/use-small-value-events', async () => {
  const { computed } = await import('vue');
  return {
    useSmallValueEvents: (): Record<string, unknown> => ({
      enabled: computed<boolean>(() => true),
      isSmallValue: (subject: SmallValueSubject): boolean => smallAssets.has(subject.asset),
      threshold: computed<number>(() => 1),
    }),
  };
});

vi.mock('@/modules/assets/use-asset-info-retrieval', async (importOriginal) => {
  const { computed } = await import('vue');
  return {
    ...await importOriginal<Record<string, unknown>>(),
    useAssetInfoRetrieval: (): Record<string, unknown> => ({
      useAssetInfo: (): unknown => computed<{ symbol: string }>(() => ({ symbol: 'ETH' })),
    }),
  };
});

describe('historyEventAsset', () => {
  function mountAsset(overrides: Parameters<typeof createOnlineHistoryEvent>[0] = {}): VueWrapper {
    return mount(HistoryEventAsset, {
      global: {
        provide: libraryDefaults,
        stubs: {
          AssetAmountDisplay: true,
          AssetDetails: true,
          AssetDetailsMenuContent: true,
          AssetValueDisplay: true,
          FiatDisplay: { props: ['value'], template: '<span>{{ value.toString() }}</span>' },
        },
      },
      props: { event: createOnlineHistoryEvent({ asset: 'ETH', ...overrides }) },
    });
  }

  beforeEach(() => {
    smallAssets.clear();
  });

  it('should show an event worth at least the threshold as is', () => {
    const wrapper = mountAsset();

    expect(wrapper.find('[data-testid=event-asset]').classes()).not.toContain('opacity-50');
    expect(wrapper.find('[data-testid=event-small-value]').exists()).toBe(false);
  });

  it('should dim a small value event and mark it with the threshold', () => {
    smallAssets.add('ETH');
    const wrapper = mountAsset();

    expect(wrapper.find('[data-testid=event-asset]').classes()).toContain('opacity-50');
    expect(wrapper.find('[data-testid=event-small-value]').text()).toBe('transactions.events.small_value.below 1');
  });

  it('should leave an informational event alone, since it shows no value', () => {
    smallAssets.add('ETH');
    const wrapper = mountAsset({ eventType: 'informational' });

    expect(wrapper.find('[data-testid=event-asset]').classes()).not.toContain('opacity-50');
    expect(wrapper.find('[data-testid=event-small-value]').exists()).toBe(false);
  });
});
