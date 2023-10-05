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
  <div>
    <VList
      nav
      class="navigation-menu"
      :class="{ 'navigation-menu--mini': isMini }"
    >
      <VListItemGroup>
        <template v-for="(navItem, i) in navItems">
          <VListItem
            v-if="navItem.type === 'item'"
            :key="i"
            :class="`navigation-menu__item navigation__${navItem.class}`"
            active-class="navigation-menu__item--active"
            :to="navItem.route"
          >
            <NavigationMenuItem
              :show-tooltips="isMini"
              :text="navItem.text"
              :icon="navItem.icon"
              :image="navItem.image"
              :icon-component="navItem.component"
            />
          </VListItem>
          <VListGroup v-else-if="navItem.type === 'group'" :key="i">
            <template #activator>
              <NavigationMenuItem
                :show-tooltips="isMini"
                :text="navItem.text"
                :icon="navItem.icon"
                :icon-component="navItem.component"
                :image="navItem.image"
                :class="`navigation-menu__item navigation__${navItem.class}`"
              />
            </template>
            <div
              class="navigation-submenu"
              :class="{ 'navigation-submenu--mini': isMini }"
            >
              <VListItem
                v-for="(subNavItem, si) in navItem.items"
                :key="si"
                :class="`navigation-menu__item navigation__${subNavItem.class}`"
                active-class="navigation-menu__item--active"
                :to="subNavItem.route"
              >
                <template #default="{ active }">
                  <NavigationMenuItem
                    :show-tooltips="isMini"
                    :text="subNavItem.text"
                    :icon="subNavItem.icon"
                    :image="subNavItem.image"
                    :icon-component="subNavItem.component"
                    :active="active"
                    sub-menu
                  />
                </template>
              </VListItem>
            </div>
          </VListGroup>
          <VDivider
            v-else-if="navItem.type === 'divider'"
            :key="i"
            class="my-2"
          />
        </template>
      </VListItemGroup>
    </VList>
  </div>
</template>

<style scoped lang="scss">
:deep(.v-list-item) {
  border-radius: 0.25rem;
  padding: 0 0.75rem;
  margin-bottom: 0 !important;
}

.navigation-menu {
  &__item {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.v-list-item__icon) {
      @apply text-rui-text-secondary;
    }

    &--active {
      :deep(.v-list-item__icon) {
        /* stylelint-enable selector-class-pattern,selector-nested-pattern */
        @apply text-white;
      }

      :deep(.nav-icon) {
        opacity: 1 !important;
        filter: brightness(0) invert(100%);
      }
      @apply bg-rui-primary font-bold;
      @apply text-white;
    }
  }

  &--mini {
    padding: 0;

    :deep(.v-list-item) {
      padding-left: 1.5rem;
      justify-content: center;

      .v-list-item {
        &__content {
          display: none !important;
        }
      }
    }
  }
}

.navigation-submenu {
  :deep(.v-list-item) {
    padding-left: 3rem;
    min-height: 0;
  }

  &--mini {
    background: var(--v-rotki-light-grey-darken1);

    :deep(.v-list-item) {
      padding-left: 1.5rem;
    }
  }
}

.theme {
  &--dark {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.navigation-submenu--mini) {
      background: var(--v-secondary-lighten1);
    }
    /* stylelint-enable selector-class-pattern,selector-nested-pattern */
  }
}
</style>
