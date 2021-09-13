<template>
  <v-tabs
    v-model="selectedTab"
    fixed-tabs
    height="36px"
    hide-slider
    :show-arrows="xsOnly"
    active-class="tab-navigation__tabs__tab--active"
    class="tab-navigation__tabs py-3"
  >
    <v-tab
      v-for="tab in visibleTabs"
      v-show="visibleTabs.length > 1 && !tab.hideHeader"
      :key="tab.name"
      :to="tab.routeTo"
      class="tab-navigation__tabs__tab"
      :class="getClass(tab.routeTo)"
    >
      <div>{{ tab.name }}</div>
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
      <v-container v-if="isDev">
        <router-view v-if="isRouterVisible($route.path, tab)" />
      </v-container>
      <keep-alive v-else>
        <v-container>
          <router-view v-if="isRouterVisible($route.path, tab)" />
        </v-container>
      </keep-alive>
    </v-tab-item>
  </v-tabs>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';

export interface TabContent {
  readonly name: string;
  readonly routeTo: string;
  readonly hidden?: boolean;
  readonly hideHeader?: boolean;
}

export default defineComponent({
  name: 'TabNavigation',
  props: {
    tabContents: { required: true, type: Array as PropType<TabContent[]> },
    noContentMargin: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { tabContents } = toRefs(props);
    const visibleTabs = computed(() => {
      return tabContents.value.filter(({ hidden }) => !hidden);
    });
    const getClass = (route: string) => {
      return route.toLowerCase().replace('/', '').replace(/\//g, '__');
    };
    const selectedTab = ref('');
    const isRouterVisible = (route: string, tab: TabContent) => {
      return (
        route.indexOf(tab.routeTo) >= 0 && tab.routeTo === selectedTab.value
      );
    };

    return {
      isDev: process.env.NODE_ENV === 'development',
      visibleTabs,
      selectedTab,
      getClass,
      isRouterVisible
    };
  },
  computed: {
    xsOnly(): boolean {
      return this.$vuetify.breakpoint.xsOnly;
    }
  }
});
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

        &__content {
          padding-left: 12px;
          padding-right: 12px;
        }
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
    }

    &__tab-item {
      &--content-margin {
        margin-top: 36px;
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
