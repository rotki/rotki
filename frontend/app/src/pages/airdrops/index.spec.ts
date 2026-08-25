import type { AirdropWithIndex } from '@/pages/airdrops/airdrop-rows';
import type { useAirdropsPage } from '@/pages/airdrops/use-airdrops-page';
import { bigNumberify } from '@rotki/common';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick, type Ref } from 'vue';
import AirdropsPage from '@/pages/airdrops/index.vue';

const fetchAirdrops = vi.fn(async (): Promise<void> => {});
const expand = vi.fn();

interface PageState {
  hideUnknownAlert: boolean;
  loading: boolean;
  rows: AirdropWithIndex[];
  status: string;
  /** The alert's dismiss flag, published back so a test can watch the page write it. */
  modelHideUnknownAlert?: Ref<boolean>;
}

const pageState = vi.hoisted((): PageState => ({
  hideUnknownAlert: false,
  loading: false,
  rows: [],
  status: '',
}));

vi.mock('@/pages/airdrops/use-airdrops-page', async () => {
  const { computed, ref, shallowRef } = await import('vue');
  return {
    useAirdropsPage: (): ReturnType<typeof useAirdropsPage> => {
      pageState.modelHideUnknownAlert = shallowRef(pageState.hideUnknownAlert);
      return {
        // The real four; a cell slot only renders for a column that is actually in `cols`.
        cols: computed(() => [
          { key: 'source', label: 'Source' },
          { key: 'address', label: 'Address' },
          { align: 'end', key: 'amount', label: 'Amount' },
          { key: 'claimed', label: 'Status' },
        ]),
        expand,
        fetchAirdrops,
        fields: [],
        loading: computed(() => pageState.loading),
        modelExpanded: ref([]),
        modelHideUnknownAlert: pageState.modelHideUnknownAlert,
        modelPagination: ref(undefined),
        modelPillParams: computed({ get: () => ({}), set: () => {} }),
        modelSort: ref([]),
        pillLabels: computed(() => ({
          add: 'add',
          clear: 'clear',
          empty: 'empty',
          narrow: 'narrow',
          narrowEmpty: 'narrowEmpty',
          remove: 'remove',
          search: 'search',
          syntax: 'syntax',
        })),
        refreshTooltip: computed(() => 'refresh the airdrops'),
        rows: computed(() => pageState.rows),
        status: computed(() => pageState.status),
      };
    },
  };
});

/**
 * Declared rather than written inline in `stubs` so its props are typed at the assertion site;
 * `findComponent` by name alone yields a wrapper whose `props()` accepts nothing.
 */
const DataTableStub = defineComponent({
  name: 'DataTableStub',
  props: {
    cols: { default: () => [], type: Array },
    expanded: { default: () => [], type: Array },
    loading: { default: false, type: Boolean },
    pagination: { default: undefined, type: Object },
    rows: { default: () => [], type: Array },
    sort: { default: () => [], type: [Array, Object] },
  },
  template: '<div />',
});

/**
 * The unknown-status alert. Stubbed so its `close` event can be emitted: without the Rui plugin
 * installed `RuiAlert` does not resolve to a component here, and the point of the test is the
 * page's `@close` binding rather than the alert's own dismiss control.
 */
const AlertStub = defineComponent({
  emits: ['close'],
  name: 'AlertStub',
  props: { closeable: { default: false, type: Boolean }, type: { default: 'info', type: String } },
  template: '<div><slot /></div>',
});

function row(index: number, source: string): AirdropWithIndex {
  return { address: '0xaaa', amount: bigNumberify(index + 1), index, source };
}

describe('pages/airdrops/index', () => {
  let wrapper: VueWrapper<InstanceType<typeof AirdropsPage>>;

  function mountPage(): VueWrapper<InstanceType<typeof AirdropsPage>> {
    return mount(AirdropsPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          PillFilterBar: { props: ['params', 'fields', 'labels'], template: '<div data-testid="pill-bar-stub" />' },
          RuiAlert: AlertStub,
          RuiDataTable: DataTableStub,
          TablePageLayout: { props: ['title'], template: '<div><slot name="buttons" /><slot /></div>' },
        },
      },
    });
  }

  function hideAlertModel(): Ref<boolean> {
    const model = pageState.modelHideUnknownAlert;
    if (!model)
      throw new Error('mount the page first');

    return model;
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.hideUnknownAlert = false;
    pageState.loading = false;
    pageState.rows = [];
    pageState.status = '';
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should hand the rows and columns to the table', () => {
    pageState.rows = [row(0, 'uniswap'), row(1, 'cow')];

    wrapper = mountPage();

    const table = wrapper.findComponent(DataTableStub);
    expect(table.props('rows')).toHaveLength(2);
    expect(table.props('cols')).toHaveLength(4);
  });

  it('should pass the loading state to the table', () => {
    pageState.loading = true;

    wrapper = mountPage();

    expect(wrapper.findComponent(DataTableStub).props('loading')).toBe(true);
  });

  it('should refetch from the refresh button', async () => {
    wrapper = mountPage();

    await wrapper.find('[data-testid=airdrop-refresh]').trigger('click');

    expect(fetchAirdrops).toHaveBeenCalledTimes(1);
  });

  /**
   * The status chip restates the claimed/missed/unclaimed decision that `matchesStatus` makes for
   * the filter, so the two can drift. These mount the real data table, which is the only way its
   * cell slots render at all.
   */
  describe('the status cell', () => {
    function mountWithRealTable(): VueWrapper<InstanceType<typeof AirdropsPage>> {
      return mount(AirdropsPage, {
        global: {
          plugins: [createPinia()],
          provide: libraryDefaults,
          stubs: {
            AirdropDisplay: { props: ['source', 'iconUrl', 'icon'], template: '<div />' },
            AssetAmountDisplay: { props: ['asset', 'amount'], template: '<div data-testid="asset-amount" />' },
            ExternalLink: { props: ['url', 'custom'], template: '<div data-testid="external-link"><slot /></div>' },
            HashLink: { props: ['text', 'location'], template: '<div />' },
            PillFilterBar: { props: ['params', 'fields', 'labels'], template: '<div />' },
            PoapDeliveryAirdrops: { props: ['items'], template: '<div data-testid="poap-details" />' },
            TablePageLayout: { props: ['title'], template: '<div><slot name="buttons" /><slot /></div>' },
            ValueDisplay: { props: ['value'], template: '<div data-testid="value-only" />' },
          },
        },
      });
    }

    it('should read a claimed row as claimed', async () => {
      pageState.rows = [{ ...row(0, 'uniswap'), asset: 'UNI', claimed: true, hasDecoder: true }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.text()).toContain('common.claimed');
    });

    it('should read an unclaimed row whose cutoff has passed as missed', async () => {
      pageState.rows = [{
        ...row(0, 'cow'),
        asset: 'COW',
        claimed: false,
        cutoffTime: Math.floor(Date.now() / 1000) - 100,
        hasDecoder: true,
      }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.text()).toContain('common.missed');
    });

    it('should read an unclaimed row whose cutoff is ahead as unclaimed', async () => {
      pageState.rows = [{
        ...row(0, 'cow'),
        asset: 'COW',
        claimed: false,
        cutoffTime: Math.floor(Date.now() / 1000) + 1000,
        hasDecoder: true,
      }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.text()).toContain('common.unclaimed');
    });

    it('should read a row with no decoder as unknown, whatever its claimed flag says', async () => {
      pageState.rows = [{ ...row(0, 'mystery'), claimed: true }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.text()).toContain('common.unknown');
      expect(wrapper.text()).not.toContain('common.claimed');
    });

    it('should show the amount against its asset when the row has one', async () => {
      pageState.rows = [{ ...row(0, 'uniswap'), asset: 'UNI', hasDecoder: true }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.find('[data-testid=asset-amount]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=value-only]').exists()).toBe(false);
    });

    it('should fall back to a bare value when the row names no asset', async () => {
      pageState.rows = [{ ...row(0, 'uniswap'), hasDecoder: true }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.find('[data-testid=value-only]').exists()).toBe(true);
      expect(wrapper.find('[data-testid=asset-amount]').exists()).toBe(false);
    });

    it('should count the deliveries instead of an amount for a poap row', async () => {
      pageState.rows = [{
        ...row(0, 'poap'),
        details: [
          { assets: [], event: 'devcon', link: 'l', name: 'n' },
          { assets: [], event: 'ethcc', link: 'l', name: 'n' },
        ],
      }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.find('[data-testid=asset-amount]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=value-only]').exists()).toBe(false);
      expect(wrapper.text()).toContain('2');
    });

    it('should offer an external link for a row that is not a poap delivery', async () => {
      pageState.rows = [{ ...row(0, 'uniswap'), asset: 'UNI', hasDecoder: true, link: 'https://uni' }];

      wrapper = mountWithRealTable();
      await nextTick();

      expect(wrapper.find('[data-testid=external-link]').exists()).toBe(true);
    });
  });

  describe('the unknown-status alert', () => {
    it('should stay hidden while no status is chosen', () => {
      wrapper = mountPage();

      expect(wrapper.find('[data-testid=airdrop-unknown-alert]').exists()).toBe(false);
    });

    it('should show once the unknown status is chosen', () => {
      pageState.status = 'unknown';

      wrapper = mountPage();

      expect(wrapper.find('[data-testid=airdrop-unknown-alert]').exists()).toBe(true);
    });

    it('should stay hidden on the unknown status once it has been dismissed', () => {
      pageState.status = 'unknown';
      pageState.hideUnknownAlert = true;

      wrapper = mountPage();

      expect(wrapper.find('[data-testid=airdrop-unknown-alert]').exists()).toBe(false);
    });

    it('should record the dismissal when the alert is closed', async () => {
      pageState.status = 'unknown';
      wrapper = mountPage();

      // Emitted from the alert itself, so this pins the `@close` binding. Writing the model
      // directly would pass with that binding deleted.
      wrapper.findComponent(AlertStub).vm.$emit('close');
      await nextTick();

      expect(get(hideAlertModel())).toBe(true);
      expect(wrapper.find('[data-testid=airdrop-unknown-alert]').exists()).toBe(false);
    });
  });
});
