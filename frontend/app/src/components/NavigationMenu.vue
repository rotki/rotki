<template>
  <div>
    <v-list nav class="navigation-menu" :class="{ 'pa-0': isMini }">
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
              :crypto-icon="navItem.cryptoIcon"
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
                :crypto-icon="navItem.cryptoIcon"
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
                    :crypto-icon="subNavItem.cryptoIcon"
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

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import NavigationMenuItem from '@/components/NavigationMenuItem.vue';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';

type NavItemDetails = {
  readonly text: string;
  readonly route: string;
  readonly class?: string;
  readonly icon: string;
  readonly image?: string;
  readonly component?: any;
  readonly cryptoIcon?: string;
};

type NavItem = { readonly type: 'item' } & NavItemDetails;
type NavGroupItem = {
  readonly type: 'group';
} & NavItemDetails & { items: NavItem[] };
type DividerItem = { readonly type: 'divider' };
type MenuItem = NavItem | NavGroupItem | DividerItem;

export default defineComponent({
  name: 'NavigationMenu',
  components: { NavigationMenuItem },
  props: {
    isMini: { required: false, type: Boolean, default: false }
  },
  setup() {
    const navItems: MenuItem[] = [
      {
        type: 'item',
        text: i18n.t('navigation_menu.dashboard').toString(),
        route: '/dashboard',
        class: 'dashboard',
        icon: 'mdi-monitor-dashboard'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.accounts_balances').toString(),
        route: '/accounts-balances',
        class: 'accounts-balances',
        icon: 'mdi-briefcase-variant'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.nfts').toString(),
        route: Routes.NFTS,
        class: 'nfts',
        icon: 'mdi-image-area'
      },
      {
        type: 'group',
        text: i18n.t('navigation_menu.history').toString(),
        route: '/history',
        class: 'history',
        icon: 'mdi-history',
        items: [
          {
            type: 'item',
            text: i18n.t('navigation_menu.history_sub.trades').toString(),
            route: '/history/trades',
            icon: 'mdi-shuffle-variant',
            class: 'history-trades'
          },
          {
            type: 'item',
            text: i18n
              .t('navigation_menu.history_sub.deposits_withdrawals')
              .toString(),
            route: '/history/deposits-withdrawals',
            icon: 'mdi-bank-transfer',
            class: 'deposits-withdrawals'
          },
          {
            type: 'item',
            text: i18n
              .t('navigation_menu.history_sub.ethereum_transactions')
              .toString(),
            route: '/history/transactions',
            icon: 'mdi-swap-horizontal-bold',
            class: 'eth-transactions'
          },
          {
            type: 'item',
            text: i18n
              .t('navigation_menu.history_sub.ledger_actions')
              .toString(),
            route: Routes.HISTORY_LEDGER_ACTIONS,
            icon: 'mdi-book-open-variant',
            class: 'ledger'
          }
        ]
      },
      {
        type: 'group',
        text: i18n.t('navigation_menu.defi').toString(),
        route: Routes.DEFI_OVERVIEW,
        icon: 'mdi-finance',
        class: 'defi',
        items: [
          {
            type: 'item',
            text: i18n.t('navigation_menu.defi_sub.overview').toString(),
            route: Routes.DEFI_OVERVIEW,
            icon: 'mdi-chart-box',
            class: 'defi-overview'
          },
          {
            type: 'item',
            text: i18n.t('navigation_menu.defi_sub.deposits').toString(),
            route: Routes.DEFI_DEPOSITS,
            icon: 'mdi-bank-transfer-in',
            class: 'defi-deposits'
          },
          {
            type: 'item',
            text: i18n.t('navigation_menu.defi_sub.liabilities').toString(),
            route: Routes.DEFI_LIABILITIES,
            icon: 'mdi-bank-transfer-out',
            class: 'defi-liabilities'
          },
          {
            type: 'item',
            text: i18n.t('navigation_menu.defi_sub.dex_trades').toString(),
            route: Routes.DEFI_DEX_TRADES,
            icon: 'mdi-shuffle-variant',
            class: 'defi-dex-trades'
          },
          {
            type: 'item',
            text: i18n.t('navigation_menu.defi_sub.airdrops').toString(),
            route: Routes.DEFI_AIRDROPS,
            icon: 'mdi-parachute',
            class: 'defi-airdrops'
          }
        ]
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.statistics').toString(),
        route: '/statistics',
        class: 'statistics',
        icon: 'mdi-chart-bar'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.staking').toString(),
        route: Routes.STAKING.split(':')[0],
        class: 'staking',
        icon: 'mdi-inbox-arrow-down'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.profit_loss_report').toString(),
        route: Routes.PROFIT_LOSS_REPORTS,
        class: 'profit-loss-report',
        icon: 'mdi-calculator'
      },
      {
        type: 'divider'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.manage_assets').toString(),
        route: Routes.ASSET_MANAGER,
        class: 'asset-manager',
        icon: 'mdi-database-edit'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.manage_prices').toString(),
        route: Routes.PRICE_MANAGER,
        class: 'asset-manager',
        icon: 'mdi-chart-line'
      },
      {
        type: 'divider'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.api_keys').toString(),
        route: '/settings/api-keys/rotki-premium',
        class: 'settings__api-keys',
        icon: 'mdi-key-chain-variant'
      },
      {
        type: 'item',
        text: i18n.t('navigation_menu.import_data').toString(),
        route: '/import',
        icon: 'mdi-database-import'
      }
    ];

    return {
      navItems
    };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
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

      ::v-deep {
        .nav-icon {
          opacity: 1 !important;
          filter: brightness(0) invert(100%);
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
    ::v-deep {
      .navigation-submenu {
        &--mini {
          background: var(--v-secondary-lighten1);
        }
      }
    }
  }
}
</style>
