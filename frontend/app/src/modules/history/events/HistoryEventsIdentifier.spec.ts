import { I18nTStub } from '@test/stubs/I18nT';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createOnlineHistoryEvent } from '@test/utils/history-events';
import { mount } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import HistoryEventsIdentifier from '@/modules/history/events/HistoryEventsIdentifier.vue';
import '@test/i18n';

describe('historyEventsIdentifier', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  function identifierText(location: string): string {
    return mount(HistoryEventsIdentifier, {
      global: { plugins: [pinia], stubs: { I18nT: I18nTStub } },
      props: { event: createOnlineHistoryEvent({ location }) },
    }).text();
  }

  it('should name a location by its display name, not its identifier', () => {
    useLocationStore().allLocations = { coinbaseprime: { isExchange: true, label: 'Coinbase Prime' } };

    expect(identifierText('coinbaseprime')).toContain('Coinbase Prime');
  });

  it('should fall back to the identifier while the location is unknown', () => {
    expect(identifierText('nowhere')).toContain('Nowhere');
  });
});
