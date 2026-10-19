import type { StakingInfo } from '@/pages/staking/use-staking-locations';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import StakingLocationTitle from '@/modules/staking/components/StakingLocationTitle.vue';

const push = vi.fn(async (): Promise<void> => {});

vi.mock('vue-router', () => ({
  useRouter: (): Record<string, unknown> => ({ push }),
}));

const locations: StakingInfo[] = [
  { description: '', id: 'eth2', image: 'eth.svg', name: 'ETH Staking' },
  { description: '', id: 'liquity', image: 'liquity.png', name: 'Liquity' },
  { description: '', id: 'lido-csm', image: 'lido.svg', name: 'Lido CSM' },
];

vi.mock('@/pages/staking/use-staking-locations', () => ({
  useStakingLocations: vi.fn(() => ({
    getRedirectLink: (location: string): string => `/staking/${location}`,
    overviewLink: '/staking?overview',
    staking: computed<StakingInfo[]>(() => locations),
  })),
}));

const stubs = {
  AppImage: true,
  RouterLink: {
    props: { to: { required: true, type: String } },
    template: '<a v-bind="$attrs" :href="to"><slot /></a>',
  },
  RuiIcon: { props: { name: { required: true, type: String } }, template: '<i :data-icon="name" />' },
  RuiMenu: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<div data-testid="menu" :data-open="modelValue"><slot name="activator" :attrs="{ onClick: () => $emit(\'update:modelValue\', !modelValue) }" /><div><slot /></div></div>',
  },
  RuiTextField: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: '', type: String } },
    template: '<input v-bind="$attrs" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
};

function createWrapper(): VueWrapper<InstanceType<typeof StakingLocationTitle>> {
  return mount(StakingLocationTitle, {
    global: { stubs },
    props: { location: 'liquity' },
  });
}

function options(wrapper: VueWrapper): string[] {
  return wrapper.findAll('[data-testid=staking-location-option]').map(option => option.attributes('data-location') ?? '');
}

async function search(wrapper: VueWrapper, query: string): Promise<void> {
  await wrapper.find('[data-testid=staking-location-search]').setValue(query);
}

describe('modules/staking/components/StakingLocationTitle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should link back to the location overview', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=staking-overview-link]').attributes('href')).toBe('/staking?overview');
  });

  it('should name the current location on the switcher', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=staking-location-switch-name]').text()).toBe('Liquity');
  });

  it('should list every location and mark the current one', () => {
    const wrapper = createWrapper();
    const current = wrapper.find('[data-testid=staking-location-option][data-location=liquity]');

    expect(options(wrapper)).toEqual(['eth2', 'liquity', 'lido-csm']);
    expect(current.attributes('aria-current')).toBe('page');
    expect(current.find('[data-icon=lu-check]').exists()).toBe(true);
    expect(wrapper.find('[data-location=eth2]').attributes('aria-current')).toBeUndefined();
  });

  it('should filter the locations by name, ignoring case and surrounding spaces', async () => {
    const wrapper = createWrapper();
    await search(wrapper, '  LI ');

    expect(options(wrapper)).toEqual(['liquity', 'lido-csm']);
  });

  it('should say so when nothing matches', async () => {
    const wrapper = createWrapper();
    expect(wrapper.text()).not.toContain('staking_page.no_matching_locations');

    await search(wrapper, 'kraken');

    expect(options(wrapper)).toEqual([]);
    expect(wrapper.text()).toContain('staking_page.no_matching_locations');
  });

  it('should go to a picked location and close the menu', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=staking-location-switch]').trigger('click');
    await wrapper.find('[data-location=eth2]').trigger('click');
    await flushPromises();

    expect(push).toHaveBeenCalledWith('/staking/eth2');
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
  });

  it('should only close the menu when the current location is picked', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=staking-location-switch]').trigger('click');
    await wrapper.find('[data-location=liquity]').trigger('click');
    await flushPromises();

    expect(push).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
  });

  it('should go to the first match on Enter', async () => {
    const wrapper = createWrapper();
    await search(wrapper, 'lido');
    await wrapper.find('[data-testid=staking-location-search]').trigger('keydown', { key: 'Enter' });
    await flushPromises();

    expect(push).toHaveBeenCalledWith('/staking/lido-csm');
  });

  it('should do nothing on Enter without a match', async () => {
    const wrapper = createWrapper();
    await search(wrapper, 'kraken');
    await wrapper.find('[data-testid=staking-location-search]').trigger('keydown', { key: 'Enter' });
    await flushPromises();

    expect(push).not.toHaveBeenCalled();
  });

  it('should clear the search when the menu closes', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=staking-location-switch]').trigger('click');
    await search(wrapper, 'lido');
    expect(options(wrapper)).toEqual(['lido-csm']);

    await wrapper.find('[data-testid=staking-location-switch]').trigger('click');

    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
    expect(options(wrapper)).toEqual(['eth2', 'liquity', 'lido-csm']);
  });
});
