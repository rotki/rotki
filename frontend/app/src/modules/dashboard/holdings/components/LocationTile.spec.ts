import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import LocationTile from '@/modules/dashboard/holdings/components/LocationTile.vue';
import { type LocationHolding, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { mergeLocations } from '@/modules/dashboard/holdings/core/location-holdings';

const [kraken, eth2] = mergeLocations([
  { kind: SourceKind.EXCHANGE, loading: false, location: 'kraken', value: bigNumberify(100) },
  { kind: SourceKind.MANUAL, loading: false, location: 'kraken', value: bigNumberify(20) },
  { chain: 'eth2', kind: SourceKind.BLOCKCHAIN, loading: true, value: bigNumberify(64) },
], { locationOfChain: () => undefined });

const stubs = {
  ChainIcon: { props: ['chain'], template: '<i data-testid="chain-icon" :data-chain="chain" />' },
  FiatDisplay: { props: ['value', 'loading'], template: '<span data-testid="fiat" :data-loading="loading">{{ value.toFixed() }}</span>' },
  LocationIcon: { props: ['item'], template: '<i data-testid="location-icon" :data-item="item" />' },
  PercentageDisplay: { props: ['value'], template: '<span data-testid="percentage">{{ value }}</span>' },
  RouterLink: { props: ['to'], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' },
};

function createWrapper(holding: LocationHolding, showKinds = true): VueWrapper<InstanceType<typeof LocationTile>> {
  return mount(LocationTile, {
    global: { stubs },
    props: { holding, label: 'Label', share: '12.50', showKinds, to: { name: '/locations/[identifier]' } },
    slots: { badge: '<b data-testid="badge" />' },
  });
}

describe('locationTile', () => {
  it('should link to its target and expose the place for e2e', () => {
    const tile = createWrapper(kraken).find('[data-testid=dashboard-location-tile]');

    expect(tile.attributes('data-to')).toBe(JSON.stringify({ name: '/locations/[identifier]' }));
    expect(tile.attributes('data-location')).toBe('kraken');
    expect(tile.attributes('data-chain')).toBeUndefined();
  });

  it('should mark each kind held at a place held through several', () => {
    const wrapper = createWrapper(kraken);

    expect(wrapper.findAll('[data-testid=dashboard-location-tile-kinds] i').map(mark => mark.attributes('data-kind'))).toEqual(['exchange', 'manual']);
  });

  it('should drop the kind marks when the strip is narrowed to one kind', () => {
    expect(createWrapper(kraken, false).find('[data-testid=dashboard-location-tile-kinds]').exists()).toBe(false);
  });

  it('should use the chain icon and pass loading for a chain without a location', () => {
    const wrapper = createWrapper(eth2);

    expect(wrapper.find('[data-testid=chain-icon]').attributes('data-chain')).toBe('eth2');
    expect(wrapper.find('[data-testid=location-icon]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=fiat]').attributes('data-loading')).toBe('true');
    expect(wrapper.find('[data-testid=dashboard-location-tile]').attributes('data-chain')).toBe('eth2');
  });

  it('should render the badge slot and the share', () => {
    const wrapper = createWrapper(eth2);

    expect(wrapper.find('[data-testid=badge]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=percentage]').text()).toBe('12.50');
  });
});
