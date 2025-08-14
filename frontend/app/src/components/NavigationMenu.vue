<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import NavigationMenuItem from '@/components/NavigationMenuItem.vue';
import { useAppRoutes } from '@/router/routes';

interface NavItemDetails {
  readonly text: string;
  readonly route: RouteLocationRaw;
  readonly class?: string;
  readonly icon: RuiIcons;
  readonly image?: string;
  readonly component?: any;
}

interface NavItem extends NavItemDetails {
  readonly type: 'item';
}

interface NavGroupItem extends NavItemDetails {
  readonly type: 'group';
  items: NavItem[];
}

interface DividerItem {
  readonly type: 'divider';
}

type MenuItem = NavItem | NavGroupItem | DividerItem;

withDefaults(
  defineProps<{
    isMini?: boolean;
  }>(),
  {
    isMini: false,
  },
);

const { appRoutes } = useAppRoutes();
const Routes = get(appRoutes);
const navItems: MenuItem[] = [
  {
    class: 'dashboard',
    type: 'item',
    ...Routes.DASHBOARD,
  },
  {
    class: 'accounts',
    type: 'group',
    ...Routes.ACCOUNTS,
    items: [
      {
        class: 'accounts-evm',
        type: 'item',
        ...Routes.ACCOUNTS_EVM,
      },
      {
        class: 'accounts-bitcoin',
        type: 'item',
        ...Routes.ACCOUNTS_BITCOIN,
      },
      {
        class: 'accounts-substrate',
        type: 'item',
        ...Routes.ACCOUNTS_SUBSTRATE,
      },
    ],
  },
  {
    class: 'balances',
    type: 'group',
    ...Routes.BALANCES,
    items: [
      {
        class: 'balances-blockchain',
        type: 'item',
        ...Routes.BALANCES_BLOCKCHAIN,
      },
      {
        class: 'balances-exchange',
        type: 'item',
        ...Routes.BALANCES_EXCHANGE,
      },
      {
        class: 'balances-manual',
        type: 'item',
        ...Routes.BALANCES_MANUAL,
      },
      {
        class: 'balances-non-fungible',
        type: 'item',
        ...Routes.BALANCES_NON_FUNGIBLE,
      },
    ],
  },
  {
    class: 'history',
    type: 'item',
    ...Routes.HISTORY,
  },
  {
    class: 'onchain',
    type: 'group',
    ...Routes.ONCHAIN,
    items: [
      {
        class: 'onchain-send',
        type: 'item',
        ...Routes.ONCHAIN_SEND,
      },
    ],
  },
  {
    class: 'staking',
    type: 'item',
    ...Routes.STAKING,
    route: '/staking',
  },
  {
    class: 'statistics',
    type: 'group',
    ...Routes.STATISTICS,
    items: [
      {
        class: 'statistics-graph',
        type: 'item',
        ...Routes.STATISTICS_GRAPHS,
      },
      {
        class: 'statistics-history-events',
        type: 'item',
        ...Routes.STATISTICS_HISTORY_EVENTS,
      },
    ],
  },
  {
    class: 'profit-loss-report',
    type: 'item',
    ...Routes.PROFIT_LOSS_REPORTS,
  },
  {
    class: 'airdrops',
    type: 'item',
    ...Routes.AIRDROPS,
  },
  {
    class: 'nfts',
    type: 'item',
    ...Routes.NFTS,
  },
  {
    type: 'divider',
  },
  {
    class: 'tag-manager',
    type: 'item',
    ...Routes.TAG_MANAGER,
  },
  {
    class: 'asset-manager',
    type: 'group',
    ...Routes.ASSET_MANAGER,
    items: [
      {
        class: 'asset-manager-managed',
        type: 'item',
        ...Routes.ASSET_MANAGER_MANAGED,
      },
      {
        class: 'asset-manager-custom',
        type: 'item',
        ...Routes.ASSET_MANAGER_CUSTOM,
      },
      {
        class: 'asset-manager-more',
        type: 'item',
        ...Routes.ASSET_MANAGER_MORE,
      },
    ],
  },
  {
    class: 'price-manager',
    type: 'group',
    ...Routes.PRICE_MANAGER,
    items: [
      {
        class: 'price-manager-latest',
        type: 'item',
        ...Routes.PRICE_MANAGER_LATEST,
      },
      {
        class: 'price-manager-historic',
        type: 'item',
        ...Routes.PRICE_MANAGER_HISTORIC,
      },
    ],
  },
  {
    class: 'address-book-manager',
    type: 'item',
    ...Routes.ADDRESS_BOOK_MANAGER,
  },
  {
    type: 'divider',
  },
  {
    class: 'api-keys',
    type: 'group',
    ...Routes.API_KEYS,
    items: [
      {
        class: 'api-keys-premium',
        type: 'item',
        ...Routes.API_KEYS_ROTKI_PREMIUM,
      },
      {
        class: 'api-keys-exchanges',
        type: 'item',
        ...Routes.API_KEYS_EXCHANGES,
      },
      {
        class: 'api-keys-external-services',
        type: 'item',
        ...Routes.API_KEYS_EXTERNAL_SERVICES,
      },
    ],
  },
  {
    type: 'item',
    ...Routes.IMPORT,
  },
  {
    type: 'divider',
  },
  {
    type: 'item',
    ...Routes.CALENDAR,
  },
];

const route = useRoute();
const router = useRouter();

function isRouteMatch(location: RouteLocationRaw) {
  return route.path.startsWith(router.resolve(location).path);
}
</script>

<template>
  <div
    class="p-3"
    :class="{ '!p-0': isMini }"
  >
    <template
      v-for="(navItem, i) in navItems"
      :key="i"
    >
      <RouterLink
        v-if="navItem.type === 'item'"
        :to="navItem.route"
        custom
      >
        <template #default="{ isActive, href }">
          <a :href="href">
            <NavigationMenuItem
              :class="`navigation__${navItem.class}`"
              :mini="isMini"
              :text="navItem.text"
              :icon="navItem.icon"
              :image="navItem.image"
              :active="isActive || isRouteMatch(navItem.route)"
              :icon-component="navItem.component"
            />
          </a>
        </template>
      </RouterLink>
      <template v-else-if="navItem.type === 'group'">
        <RouterLink
          :key="navItem.route.toString()"
          :to="navItem.route"
          custom
        >
          <template #default="{ isActive: isActiveParent }">
            <NavigationMenuItem
              :class="`navigation__${navItem.class}`"
              :mini="isMini"
              :text="navItem.text"
              :icon="navItem.icon"
              :icon-component="navItem.component"
              :image="navItem.image"
              :active="isActiveParent"
              parent
            >
              <div :class="{ 'bg-rui-grey-200 dark:bg-rui-grey-800': isMini }">
                <RouterLink
                  v-for="(subNavItem, si) in navItem.items"
                  :key="si"
                  :to="subNavItem.route"
                  custom
                >
                  <template #default="{ isActive, href }">
                    <a :href="href">
                      <NavigationMenuItem
                        :class="`navigation__${subNavItem.class}`"
                        :mini="isMini"
                        :text="subNavItem.text"
                        :icon="subNavItem.icon"
                        :image="subNavItem.image"
                        :icon-component="subNavItem.component"
                        :active="isActive || isRouteMatch(subNavItem.route)"
                        sub-menu
                      />
                    </a>
                  </template>
                </RouterLink>
              </div>
            </NavigationMenuItem>
          </template>
        </RouterLink>
      </template>
      <RuiDivider
        v-else-if="navItem.type === 'divider'"
        :key="i"
        class="my-2"
      />
    </template>
  </div>
</template>
