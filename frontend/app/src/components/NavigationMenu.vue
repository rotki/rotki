<template>
  <div>
    <v-list nav class="navigation-menu">
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
              :show-tooltips="showTooltips"
              :text="navItem.text"
              :icon="navItem.icon"
              :image="navItem.image"
              :icon-component="navItem.component"
              :crypto-icon="navItem.cryptoIcon"
            />
          </v-list-item>
          <v-list-group v-else-if="navItem.type === 'group'" :key="i">
            <template #activator>
              <navigation-menu-item
                :show-tooltips="showTooltips"
                :text="navItem.text"
                :icon="navItem.icon"
                :crypto-icon="navItem.cryptoIcon"
                :icon-component="navItem.component"
                :image="navItem.image"
                :class="`navigation__${navItem.class}`"
              />
            </template>
            <v-list-item
              v-for="(subNavItem, si) in navItem.items"
              :key="si"
              :class="`navigation__${subNavItem.class}`"
              active-class="navigation-menu__item--active"
              :to="subNavItem.route"
            >
              <template #default="{ active }">
                <navigation-menu-item
                  :show-tooltips="showTooltips"
                  :text="subNavItem.text"
                  :icon="subNavItem.icon"
                  :image="subNavItem.image"
                  :icon-component="subNavItem.component"
                  :crypto-icon="subNavItem.cryptoIcon"
                  :active="active"
                />
              </template>
            </v-list-item>
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
import { VueConstructor } from 'vue';
import { Component, Vue, Prop } from 'vue-property-decorator';
import GitcoinIcon from '@/components/icons/GitcoinIcon.vue';
import NavigationMenuItem from '@/components/NavigationMenuItem.vue';
import { Routes } from '@/router/routes';

type NavItemDetails = {
  readonly text: string;
  readonly route: string;
  readonly class?: string;
  readonly icon: string;
  readonly image?: string;
  readonly component?: VueConstructor;
  readonly cryptoIcon?: string;
};

type NavItem = { readonly type: 'item' } & NavItemDetails;
type NavGroupItem = {
  readonly type: 'group';
} & NavItemDetails & { items: NavItem[] };
type DividerItem = { readonly type: 'divider' };
type MenuItem = NavItem | NavGroupItem | DividerItem;

@Component({
  components: { NavigationMenuItem }
})
export default class NavigationMenu extends Vue {
  @Prop({ required: false, default: false })
  showTooltips!: boolean;

  readonly navItems: MenuItem[] = [
    {
      type: 'item',
      text: this.$tc('navigation_menu.dashboard'),
      route: '/dashboard',
      class: 'dashboard',
      icon: 'mdi-monitor-dashboard'
    },
    {
      type: 'item',
      text: this.$tc('navigation_menu.accounts_balances'),
      route: '/accounts-balances',
      class: 'accounts-balances',
      icon: 'mdi-briefcase-variant'
    },
    {
      type: 'group',
      text: this.$tc('navigation_menu.history'),
      route: '/history',
      class: 'history',
      icon: 'mdi-history',
      items: [
        {
          type: 'item',
          text: this.$tc('navigation_menu.history_sub.trades'),
          route: '/history/trades',
          icon: 'mdi-shuffle-variant',
          class: 'history-trades'
        },
        {
          type: 'item',
          text: this.$tc('navigation_menu.history_sub.deposits_withdrawals'),
          route: '/history/deposits-withdrawals',
          icon: 'mdi-bank-transfer',
          class: 'deposits-withdrawals'
        },
        {
          type: 'item',
          text: this.$tc('navigation_menu.history_sub.ethereum_transactions'),
          route: '/history/transactions',
          icon: 'mdi-swap-horizontal-bold',
          class: 'eth-transactions'
        },
        {
          type: 'item',
          text: this.$t(
            'navigation_menu.history_sub.ledger_actions'
          ).toString(),
          route: Routes.HISTORY_LEDGER_ACTIONS,
          icon: 'mdi-book-open-variant',
          class: 'ledger'
        },
        {
          type: 'item',
          text: this.$t(
            'navigation_menu.history_sub.gitcoin_grants'
          ).toString(),
          route: Routes.HISTORY_GITCOIN,
          icon: '',
          component: GitcoinIcon,
          class: 'gitcoin'
        }
      ]
    },
    {
      type: 'group',
      text: this.$tc('navigation_menu.defi'),
      route: Routes.DEFI_OVERVIEW,
      icon: 'mdi-finance',
      class: 'defi',
      items: [
        {
          type: 'item',
          text: this.$tc('navigation_menu.defi_sub.overview'),
          route: Routes.DEFI_OVERVIEW,
          icon: 'mdi-chart-box',
          class: 'defi-overview'
        },
        {
          type: 'item',
          text: this.$tc('navigation_menu.defi_sub.deposits'),
          route: Routes.DEFI_DEPOSITS,
          icon: 'mdi-bank-transfer-in',
          class: 'defi-deposits'
        },
        {
          type: 'item',
          text: this.$tc('navigation_menu.defi_sub.liabilities'),
          route: Routes.DEFI_LIABILITIES,
          icon: 'mdi-bank-transfer-out',
          class: 'defi-liabilities'
        },
        {
          type: 'item',
          text: this.$tc('navigation_menu.defi_sub.dex_trades'),
          route: Routes.DEFI_DEX_TRADES,
          icon: 'mdi-shuffle-variant',
          class: 'defi-dex-trades'
        },
        {
          type: 'item',
          text: this.$t('navigation_menu.defi_sub.airdrops').toString(),
          route: Routes.DEFI_AIRDROPS,
          icon: 'mdi-parachute',
          class: 'defi-airdrops'
        }
      ]
    },
    {
      type: 'item',
      text: this.$tc('navigation_menu.statistics'),
      route: '/statistics',
      class: 'statistics',
      icon: 'mdi-chart-bar'
    },
    {
      type: 'group',
      text: this.$tc('navigation_menu.staking'),
      route: Routes.STAKING,
      class: 'staking',
      icon: 'mdi-inbox-arrow-down',
      items: [
        {
          type: 'item',
          text: `${this.$t('navigation_menu.staking_sub.eth2')}`,
          route: Routes.STAKING_ETH2,
          icon: '',
          cryptoIcon: 'ETH2',
          class: 'staking-adex'
        },
        {
          type: 'item',
          text: `${this.$t('navigation_menu.staking_sub.adex')}`,
          route: Routes.STAKING_ADEX,
          icon: '',
          cryptoIcon: 'ADX',
          class: 'staking-adex'
        }
      ]
    },
    {
      type: 'item',
      text: this.$tc('navigation_menu.profit_loss_report'),
      route: Routes.PROFIT_LOSS_REPORT,
      class: 'profit-loss-report',
      icon: 'mdi-calculator'
    },
    {
      type: 'divider'
    },
    {
      type: 'item',
      text: this.$t('navigation_menu.manage_assets').toString(),
      route: Routes.ASSET_MANAGER,
      class: 'asset-manager',
      icon: 'mdi-database-edit'
    },
    {
      type: 'item',
      text: this.$t('navigation_menu.manage_prices').toString(),
      route: Routes.PRICE_MANAGER,
      class: 'asset-manager',
      icon: 'mdi-chart-line'
    },
    {
      type: 'divider'
    },
    {
      type: 'item',
      text: this.$tc('navigation_menu.api_keys'),
      route: '/settings/api-keys/rotki-premium',
      class: 'settings__api-keys',
      icon: 'mdi-key-chain-variant'
    },
    {
      type: 'item',
      text: this.$tc('navigation_menu.import_data'),
      route: '/import',
      icon: 'mdi-database-import'
    }
  ];
}
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
          filter: invert(100%);
        }
      }
    }
  }
}
</style>
