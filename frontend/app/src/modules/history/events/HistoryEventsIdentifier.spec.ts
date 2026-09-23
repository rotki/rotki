import { I18nTStub } from '@test/stubs/I18nT';
import { createCustomPinia } from '@test/utils/create-pinia';
import { createOnlineHistoryEvent } from '@test/utils/history-events';
import { createLocationNode as node } from '@test/utils/location-tree';
import { mount } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import HistoryEventsIdentifier from '@/modules/history/events/HistoryEventsIdentifier.vue';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import '@test/i18n';

describe('historyEventsIdentifier', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  it('should name a custom location by the name the user gave it', () => {
    useLocationTreeStore().setNodes([node('custom:luno', 'exchanges', 'Luno', { isBuiltin: false })]);
    const wrapper = mount(HistoryEventsIdentifier, {
      global: { plugins: [pinia], stubs: { I18nT: I18nTStub } },
      props: { event: createOnlineHistoryEvent({ location: 'custom:luno' }) },
    });
    expect(wrapper.text()).toContain('Luno');
    expect(wrapper.text()).not.toContain('custom:luno');
  });

  it('should fall back to the identifier while the location is unknown', () => {
    const wrapper = mount(HistoryEventsIdentifier, {
      global: { plugins: [pinia], stubs: { I18nT: I18nTStub } },
      props: { event: createOnlineHistoryEvent({ location: 'nowhere' }) },
    });
    expect(wrapper.text()).toContain('Nowhere');
  });
});
