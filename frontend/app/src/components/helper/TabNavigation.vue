<template>
  <v-tabs
    v-model="selectedTab"
    fixed-tabs
    height="36px"
    hide-slider
    active-class="tab-navigation__tabs__tab--active"
    class="tab-navigation__tabs py-6"
  >
    <v-tab
      v-for="tab in visibleTabs"
      v-show="visibleTabs.length > 1 && !tab.hideHeader"
      :key="tab.name"
      :to="tab.routeTo"
      class="tab-navigation__tabs__tab"
      :class="getClass(tab.routeTo)"
    >
      {{ tab.name }}
    </v-tab>
    <v-tab-item
      v-for="tab of tabContents"
      :key="tab.id"
      :value="tab.routeTo"
      :class="
        !noContentMargin
          ? 'tab-navigation__tabs__tab-item--content-margin'
          : null
      "
      class="tab-navigation__tabs__tab-item"
    >
      <keep-alive>
        <router-view
          v-if="
            $route.path.indexOf(tab.routeTo) >= 0 && tab.routeTo === selectedTab
          "
        />
      </keep-alive>
    </v-tab-item>
  </v-tabs>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

export interface TabContent {
  readonly name: string;
  readonly routeTo: string;
  readonly hidden?: boolean;
  readonly hideHeader?: boolean;
}

@Component({})
export default class TabNavigation extends Vue {
  @Prop({ required: true, type: Array })
  tabContents!: TabContent[];
  @Prop({ required: false, type: Boolean, default: false })
  noContentMargin!: boolean;

  selectedTab: string = '';

  get visibleTabs(): TabContent[] {
    return this.tabContents.filter(t => !t.hidden);
  }

  getClass(route: string): string {
    return route.toLowerCase().replace('/', '').replace(/\//g, '__');
  }
}
</script>

<style scoped lang="scss">
@mixin start() {
  border-radius: 8px 0 0 8px;
  border-right: 0;
}

@mixin end() {
  border-radius: 0 8px 8px 0;
  border-left: 0;
}

.tab-navigation {
  &__tabs {
    ::v-deep {
      .v-tabs-bar {
        background-color: var(--v-rotki-light-grey-base) !important;
      }

      /* stylelint-disable scss/selector-nest-combinators,selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
      .theme {
        &--dark {
          &.v-tabs-bar {
            background-color: transparent !important;
          }
          .tab-navigation__tabs__tab:not(.tab-navigation__tabs__tab--active) {
            background: var(--v-dark-base) !important;
          }
        }
      }
      /* stylelint-enable scss/selector-nest-combinators,selector-class-pattern,selector-nested-pattern, rule-empty-line-before */

      .v-tabs-items {
        background-color: transparent !important;
      }

      .v-slide-group {
        &__prev {
          display: none !important;
        }

        &__next {
          display: none !important;
        }
      }
    }

    &__tab-item {
      &--content-margin {
        margin-top: 50px;
      }
    }

    /* stylelint-disable no-descending-specificity */

    &__tab {
      background-color: white;
      border: var(--v-rotki-light-grey-darken1) solid thin;

      &:hover {
        background-color: var(--v-rotki-light-grey-base);
      }

      a {
        border: 1px solid var(--v-primary-base);
        background-color: white;
      }

      &--active {
        color: white !important;
        background-color: var(--v-primary-base) !important;
      }

      &:first-of-type {
        &:hover {
          @include start();
        }

        @include start();
      }

      &:last-of-type {
        &:hover {
          @include end();
        }

        @include end();
      }

      /* stylelint-enable no-descending-specificity */
    }

    .v-tab {
      &:hover {
        &::before {
          border-radius: inherit;
        }
      }
    }
  }
}
</style>
