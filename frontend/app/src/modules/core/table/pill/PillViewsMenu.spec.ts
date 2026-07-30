import type { SavedViewState } from '@/modules/core/table/pill/composables/use-saved-views';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { SavedFilterLocation } from '@/modules/core/table/filtering';
import PillViewsMenu from '@/modules/core/table/pill/PillViewsMenu.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

interface FrontendPatch { savedViews?: Partial<Record<SavedFilterLocation, SavedView[]>> }

const updateFrontendSetting = vi.fn(async (_settings: FrontendPatch) => ({ success: true }));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: typeof updateFrontendSetting } => ({ updateFrontendSetting }),
}));

// RuiMenu teleports its content lazily; stub it so the activator and the content are both in the
// tree without having to open it.
const RuiMenuStub = defineComponent({
  name: 'RuiMenu',
  props: { disabled: { default: false, type: Boolean }, modelValue: { default: false, type: Boolean } },
  emits: ['update:modelValue'],
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

const location: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'matcher' },
  key: 'location',
  label: 'Location',
  multiple: false,
  operators: ['is'],
  suggest: (): string[] => ['kraken'],
  valueType: 'enum',
};

const account: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'param', paramKey: 'locationLabels', to: 'both' },
  key: 'account',
  label: 'Account',
  multiple: true,
  operators: ['is'],
  suggest: (): string[] => ['0xaaa'],
  valueType: 'enum',
};

function view(name: string, matches: SavedView['matches'] = {}): SavedView {
  return { matches, name, params: {} };
}

function createWrapper(state: SavedViewState = { matches: {}, params: {} }): VueWrapper<InstanceType<typeof PillViewsMenu>> {
  return mount(PillViewsMenu, {
    global: {
      plugins: [createCustomPinia()],
      stubs: { RuiMenu: RuiMenuStub },
    },
    props: {
      fields: [location, account],
      location: SavedFilterLocation.HISTORY_EVENTS,
      state,
    },
  });
}

function storeViews(views: SavedView[]): void {
  useSettingsRepo().updateFrontend({ savedViews: { [SavedFilterLocation.HISTORY_EVENTS]: views } });
}

describe('pillViewsMenu', () => {
  // jsdom has no layout and no `scrollIntoView`, so the call itself is what can be asserted.
  const scrollIntoView = vi.fn();

  beforeAll(() => {
    Element.prototype.scrollIntoView = scrollIntoView;
  });

  beforeEach(() => {
    updateFrontendSetting.mockClear();
  });

  it('should list the stored views with a summary of what they filter', async () => {
    const wrapper = createWrapper();
    storeViews([view('Kraken', { location: 'kraken' })]);
    await nextTick();

    const row = wrapper.get('[data-testid=pill-views-apply-0]');
    expect(row.text()).toContain('Kraken');
    expect(row.text()).toContain('Location: kraken');
  });

  it('should show the empty state when nothing is saved', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=pill-views-empty]').exists()).toBe(true);
  });

  it('should emit the applied view', async () => {
    const wrapper = createWrapper();
    storeViews([view('Kraken', { location: 'kraken' }), view('Other')]);
    await nextTick();

    await wrapper.get('[data-testid=pill-views-apply-1]').trigger('click');

    expect(wrapper.emitted('apply')?.[0]?.[0]).toMatchObject({ name: 'Other' });
  });

  it('should move the highlight with arrow keys and apply it with enter', async () => {
    const wrapper = createWrapper();
    storeViews([view('first'), view('second')]);
    await nextTick();

    const list = wrapper.get('[data-testid=pill-views-list]');
    await list.trigger('keydown', { key: 'ArrowDown' });
    await list.trigger('keydown', { key: 'Enter' });

    expect(wrapper.emitted('apply')?.[0]?.[0]).toMatchObject({ name: 'second' });
  });

  // Nothing filtered means there is nothing to name, so the input says why instead of sitting dead.
  it('should not offer to save while no filter is active', () => {
    const wrapper = createWrapper();
    expect(wrapper.get('[data-testid=pill-views-name]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=pill-views-hint]').exists()).toBe(true);
  });

  it('should save the current state under the typed name', async () => {
    const wrapper = createWrapper({ matches: { location: 'kraken' }, params: { locationLabels: ['0xaaa'] } });

    await wrapper.get('[data-testid=pill-views-name]').setValue('Kraken swaps');
    await wrapper.get('[data-testid=pill-views-save]').trigger('click');
    await nextTick();

    expect(updateFrontendSetting).toHaveBeenCalledWith({
      savedViews: {
        [SavedFilterLocation.HISTORY_EVENTS]: [{
          matches: { location: 'kraken' },
          name: 'Kraken swaps',
          params: { locationLabels: ['0xaaa'] },
        }],
      },
    });
  });

  it('should report a rejected save inline', async () => {
    const wrapper = createWrapper({ matches: { location: 'kraken' }, params: {} });
    storeViews([view('Kraken')]);
    await nextTick();

    await wrapper.get('[data-testid=pill-views-name]').setValue('kraken');
    await wrapper.get('[data-testid=pill-views-save]').trigger('click');
    await nextTick();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
    expect(wrapper.get('[data-testid=pill-views-error]').text()).toBe('table_filter.saved_views.errors.duplicate');
  });

  it('should delete the view of the clicked row', async () => {
    const wrapper = createWrapper();
    storeViews([view('a'), view('b')]);
    await nextTick();

    await wrapper.get('[data-testid=pill-views-delete-0]').trigger('click');

    expect(updateFrontendSetting).toHaveBeenCalledWith({
      savedViews: { [SavedFilterLocation.HISTORY_EVENTS]: [view('b')] },
    });
  });
  // The list scrolls once a few views are stored, and the arrow keys are handled on the list
  // itself, so nothing else can pull the highlighted row back into view.
  it('should bring the highlighted view into view as the arrows move it', async () => {
    const wrapper = createWrapper();
    storeViews([view('first'), view('second')]);
    await nextTick();
    scrollIntoView.mockClear();

    await wrapper.get('[data-testid=pill-views-list]').trigger('keydown', { key: 'ArrowDown' });

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
  });
});
