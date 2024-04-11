import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Wrapper, mount } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import AccountBalances from '@/components/accounts/AccountBalances.vue';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { createCustomPinia } from '../../../utils/create-pinia';
import { libraryDefaults } from '../../../utils/provide-defaults';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue({
    query: {
      limit: '10',
      offset: '0',
    },
  }),
  useRouter: vi.fn(),
}));

describe('accountBalances.vue', () => {
  let wrapper: Wrapper<any>;

  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    wrapper = mount(AccountBalances, {
      vuetify,
      pinia,
      propsData: {
        blockchain: Blockchain.ETH,
        balances: [],
        title: 'ETH balances',
      },
      provide: libraryDefaults,
    });
  });

  afterEach(() => {
    useSessionStore().$reset();
  });

  it('table enters into loading state when balances load', async () => {
    const { add, remove } = useTaskStore();
    add({
      id: 1,
      type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      meta: {
        title: 'test',
      },
      time: 0,
    });

    useStatusStore().setStatus({
      section: Section.BLOCKCHAIN,
      subsection: Blockchain.ETH,
      status: Status.LOADING,
    });

    await wrapper.vm.$nextTick();

    expect(
      wrapper
        .find('[data-cy=account-balances-refresh-menu]')
        .find('button')
        .attributes('disabled'),
    ).toBe('disabled');

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBeTruthy();

    remove(1);
    useStatusStore().setStatus({
      section: Section.BLOCKCHAIN,
      subsection: Blockchain.ETH,
      status: Status.LOADED,
    });
    await wrapper.vm.$nextTick();

    expect(
      wrapper
        .find('[data-cy=account-balances-refresh-menu]')
        .find('button')
        .attributes('disabled'),
    ).toBeUndefined();
    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBeFalsy();
    expect(wrapper.find('tbody tr td p').text()).toMatch('data_table.no_data');
  });
});
