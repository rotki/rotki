<template>
  <div>
    <v-list
      nav
      class="navigation-menu"
      :class="{ 'navigation-menu--mini': isMini }"
    >
      <v-list-item-group>
        <template v-for="(navItem, i) in navItems">
          <v-list-item
            v-if="navItem.type === 'item'"
            :key="i"
            :class="`navigation__${navItem.class}`"
            active-class="navigation-menu__item--active"
            :to="navItem.route"
          >
            <navigation-menu-item
              :show-tooltips="isMini"
              :text="navItem.text"
              :icon="navItem.icon"
              :image="navItem.image"
              :icon-component="navItem.component"
            />
          </v-list-item>
          <v-list-group
            v-else-if="navItem.type === 'group'"
            :key="i"
            class="mb-2"
          >
            <template #activator>
              <navigation-menu-item
                :show-tooltips="isMini"
                :text="navItem.text"
                :icon="navItem.icon"
                :icon-component="navItem.component"
                :image="navItem.image"
                :class="`navigation__${navItem.class}`"
              />
            </template>
            <div
              class="navigation-submenu"
              :class="{ 'navigation-submenu--mini': isMini }"
            >
              <v-list-item
                v-for="(subNavItem, si) in navItem.items"
                :key="si"
                :class="`navigation__${subNavItem.class}`"
                active-class="navigation-menu__item--active"
                :to="subNavItem.route"
              >
                <template #default="{ active }">
                  <navigation-menu-item
                    :show-tooltips="isMini"
                    :text="subNavItem.text"
                    :icon="subNavItem.icon"
                    :image="subNavItem.image"
                    :icon-component="subNavItem.component"
                    :active="active"
                  />
                </template>
              </v-list-item>
            </div>
          </v-list-group>
          <v-divider
            v-else-if="navItem.type === 'divider'"
            :key="i"
            class="mb-2"
          />
        </template>
      </v-list-item-group>
    </v-list>
  </div>
</template>

<script setup lang="ts">
import NavigationMenuItem from '@/components/NavigationMenuItem.vue';
import { useAppRoutes } from '@/router/routes';

type NavItemDetails = {
  readonly text: string;
  readonly route: string;
  readonly class?: string;
  readonly icon: string;
  readonly image?: string;
  readonly component?: any;
};

type NavItem = { readonly type: 'item' } & NavItemDetails;
type NavGroupItem = {
  readonly type: 'group';
} & NavItemDetails & { items: NavItem[] };
type DividerItem = { readonly type: 'divider' };
type MenuItem = NavItem | NavGroupItem | DividerItem;

defineProps({
  isMini: { required: false, type: Boolean, default: false }
});

const { appRoutes } = useAppRoutes();
const Routes = get(appRoutes);
const navItems: MenuItem[] = [
  {
    type: 'item',
    class: 'dashboard',
    ...Routes.DASHBOARD
  },
  {
    type: 'item',
    class: 'accounts-balances',
    ...Routes.ACCOUNTS_BALANCES
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
        class: 'deposits-withdrawals',
        ...Routes.HISTORY_DEPOSITS_WITHDRAWALS
      },
      {
        type: 'item',
        class: 'eth-transactions',
        ...Routes.HISTORY_TRANSACTIONS
      },
      {
        type: 'item',
        class: 'ledger',
        ...Routes.HISTORY_LEDGER_ACTIONS
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
    type: 'item',
    class: 'asset-manager',
    ...Routes.ASSET_MANAGER
  },
  {
    type: 'item',
    class: 'price-manager',
    ...Routes.PRICE_MANAGER
  },
  {
    type: 'item',
    class: 'eth-address-book-manager',
    ...Routes.ETH_ADDRESS_BOOK_MANAGER
  },
  {
    type: 'divider'
  },
  {
    type: 'item',
    class: 'settings__api-keys',
    ...Routes.API_KEYS
  },
  {
    type: 'item',
    ...Routes.IMPORT
  }
];
</script>

<style scoped lang="scss">
:deep() {
  .v-list-item {
    border-radius: 0.5rem;
    padding: 0 0.75rem;

    &:before {
      border-radius: 0.5rem;
    }
  }

  .v-list-group {
    &__header {
      &__append-icon {
        margin-left: -18px !important;
      }

      .v-list-item {
        padding-left: 0 !important;
      }
    }
  }
}

.navigation-menu {
  &__item {
    &--active {
      background-color: var(--v-primary-base);
      color: white !important;

      :deep() {
        .nav-icon {
          opacity: 1 !important;
          filter: brightness(0) invert(100%);
        }
      }
    }
  }

  &--mini {
    padding: 0;

    :deep() {
      .v-list-item {
        padding-left: 28px;
        justify-content: center;

        &__content {
          display: none !important;
        }
      }
    }
  }
}

.navigation-submenu {
  padding-left: 1rem;

  &--mini {
    padding-left: 0;
    background: var(--v-rotki-light-grey-darken1);
  }
}

.theme {
  &--dark {
    :deep() {
      .navigation-submenu {
        &--mini {
          background: var(--v-secondary-lighten1);
        }
      }
    }
  }
}
</style>
