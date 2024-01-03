<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';

interface NavItemDetails {
  readonly text: string;
  readonly route: string;
  readonly class?: string;
  readonly icon: string;
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
    isMini: false
  }
);

const { appRoutes } = useAppRoutes();
const Routes = get(appRoutes);
const navItems: MenuItem[] = [
  {
    type: 'item',
    class: 'dashboard',
    ...Routes.DASHBOARD
  },
  {
    type: 'group',
    class: 'accounts-balances',
    ...Routes.ACCOUNTS_BALANCES,
    items: [
      {
        type: 'item',
        class: 'accounts-balances-blockchain',
        ...Routes.ACCOUNTS_BALANCES_BLOCKCHAIN
      },
      {
        type: 'item',
        class: 'accounts-balances-exchange',
        ...Routes.ACCOUNTS_BALANCES_EXCHANGE
      },
      {
        type: 'item',
        class: 'accounts-balances-manual',
        ...Routes.ACCOUNTS_BALANCES_MANUAL
      },
      {
        type: 'item',
        class: 'accounts-balances-non-fungible',
        ...Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE
      }
    ]
  },
  {
    type: 'item',
    class: 'nfts',
    ...Routes.NFTS
  },
  {
    type: 'group',
    class: 'history',
    ...Routes.HISTORY,
    items: [
      {
        type: 'item',
        class: 'history-trades',
        ...Routes.HISTORY_TRADES
      },
      {
        type: 'item',
        class: 'history-deposits-withdrawals',
        ...Routes.HISTORY_DEPOSITS_WITHDRAWALS
      },
      {
        type: 'item',
        class: 'history-events',
        ...Routes.HISTORY_EVENTS
      }
    ]
  },
  {
    type: 'group',
    class: 'defi',
    ...Routes.DEFI,
    items: [
      {
        type: 'item',
        class: 'defi-overview',
        ...Routes.DEFI_OVERVIEW
      },
      {
        type: 'item',
        class: 'defi-deposits',
        ...Routes.DEFI_DEPOSITS
      },
      {
        type: 'item',
        class: 'defi-liabilities',
        ...Routes.DEFI_LIABILITIES
      },
      {
        type: 'item',
        class: 'defi-airdrops',
        ...Routes.DEFI_AIRDROPS
      }
    ]
  },
  {
    type: 'item',
    class: 'statistics',
    ...Routes.STATISTICS
  },
  {
    type: 'item',
    class: 'staking',
    ...Routes.STAKING,
    route: Routes.STAKING.route.split(':')[0]
  },
  {
    type: 'item',
    class: 'profit-loss-report',
    ...Routes.PROFIT_LOSS_REPORTS
  },
  {
    type: 'divider'
  },
  {
    type: 'group',
    class: 'asset-manager',
    ...Routes.ASSET_MANAGER,
    items: [
      {
        type: 'item',
        class: 'asset-manager-managed',
        ...Routes.ASSET_MANAGER_MANAGED
      },
      {
        type: 'item',
        class: 'asset-manager-custom',
        ...Routes.ASSET_MANAGER_CUSTOM
      },
      {
        type: 'item',
        class: 'asset-manager-newly-detected',
        ...Routes.ASSET_MANAGER_NEWLY_DETECTED
      }
    ]
  },
  {
    type: 'group',
    class: 'price-manager',
    ...Routes.PRICE_MANAGER,
    items: [
      {
        type: 'item',
        class: 'price-manager-latest',
        ...Routes.PRICE_MANAGER_LATEST
      },
      {
        type: 'item',
        class: 'price-manager-historic',
        ...Routes.PRICE_MANAGER_HISTORIC
      }
    ]
  },
  {
    type: 'item',
    class: 'address-book-manager',
    ...Routes.ADDRESS_BOOK_MANAGER
  },
  {
    type: 'divider'
  },
  {
    type: 'group',
    class: 'api-keys',
    ...Routes.API_KEYS,
    items: [
      {
        type: 'item',
        class: 'api-keys-premium',
        ...Routes.API_KEYS_ROTKI_PREMIUM
      },
      {
        type: 'item',
        class: 'api-keys-exchanges',
        ...Routes.API_KEYS_EXCHANGES
      },
      {
        type: 'item',
        class: 'api-keys-external-services',
        ...Routes.API_KEYS_EXTERNAL_SERVICES
      }
    ]
  },
  {
    type: 'item',
    ...Routes.IMPORT
  }
];
</script>

<template>
  <div class="p-2" :class="{ '!p-0': isMini }">
    <template v-for="(navItem, i) in navItems">
      <RouterLink
        v-if="navItem.type === 'item'"
        :key="i"
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
              :active="isActive"
              :icon-component="navItem.component"
            />
          </a>
        </template>
      </RouterLink>
      <NavigationMenuItem
        v-else-if="navItem.type === 'group'"
        :key="i"
        :class="`navigation__${navItem.class}`"
        :mini="isMini"
        :text="navItem.text"
        :icon="navItem.icon"
        :icon-component="navItem.component"
        :image="navItem.image"
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
                  :active="isActive"
                  sub-menu
                />
              </a>
            </template>
          </RouterLink>
        </div>
      </NavigationMenuItem>
      <RuiDivider
        v-else-if="navItem.type === 'divider'"
        :key="i"
        class="my-2"
      />
    </template>
  </div>
</template>
