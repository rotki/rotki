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
            ></navigation-menu-item>
          </v-list-item>
          <v-list-group v-else-if="navItem.type === 'group'" :key="i">
            <template #activator>
              <navigation-menu-item
                :show-tooltips="showTooltips"
                :text="navItem.text"
                :icon="navItem.icon"
                :class="`navigation__${navItem.class}`"
              ></navigation-menu-item>
            </template>
            <v-list-item
              v-for="(subNavItem, si) in navItem.items"
              :key="si"
              :class="`navigation__${subNavItem.class}`"
              active-class="navigation-menu__item--active"
              :to="subNavItem.route"
            >
              <navigation-menu-item
                :show-tooltips="showTooltips"
                :text="subNavItem.text"
                :icon="subNavItem.icon"
              ></navigation-menu-item>
            </v-list-item>
          </v-list-group>
        </template>
      </v-list-item-group>
    </v-list>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';
import NavigationMenuItem from '@/components/NavigationMenuItem.vue';

@Component({
  components: { NavigationMenuItem }
})
export default class NavigationMenu extends Vue {
  @Prop({ required: false, default: false })
  showTooltips!: boolean;

  navItems = [
    {
      type: 'item',
      text: 'Dashboard',
      route: '/dashboard',
      class: 'dashboard',
      icon: 'fa-dashboard'
    },
    {
      type: 'item',
      text: 'Accounts & Balances',
      route: '/accounts-balances',
      class: 'accounts-balances',
      icon: 'fa-briefcase'
    },
    {
      type: 'item',
      text: 'API Keys',
      route: '/settings/api-keys/rotki-premium',
      class: 'settings__api-keys',
      icon: 'fa-key'
    },
    { type: 'item', text: 'Import Data', route: '/import', icon: 'fa-upload' },
    {
      type: 'group',
      text: 'Trades',
      route: '',
      icon: 'fa-exchange',
      class: 'trades',
      items: [
        {
          type: 'item',
          text: 'OTC Trades',
          route: '/otc-trades',
          class: 'otc-trades',
          icon: 'fa-exchange'
        }
      ]
    },
    {
      type: 'group',
      text: 'DeFi',
      route: '',
      icon: 'fa-line-chart',
      class: 'defi',
      items: [
        {
          type: 'item',
          text: 'Lending',
          route: '/defi/lending',
          class: 'defi-lending',
          icon: 'fa-long-arrow-left'
        },
        {
          type: 'item',
          text: 'Borrowing',
          route: '/defi/borrowing',
          class: 'defi-borrowing',
          icon: 'fa-long-arrow-right'
        }
      ]
    },
    {
      type: 'item',
      text: 'Statistics',
      route: '/statistics',
      class: 'statistics',
      icon: 'fa-bar-chart'
    },
    {
      type: 'item',
      text: 'Tax Report',
      route: '/tax-report',
      class: 'tax-report',
      icon: 'fa-calculator'
    }
  ];
}
</script>

<style scoped lang="scss">
.navigation-menu {
  &__item {
    &--active {
      background-color: var(--v-primary-base);
      color: white !important;
    }
  }
}

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
</style>
