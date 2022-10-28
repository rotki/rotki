<template>
  <v-container>
    <v-tabs
      v-model="selectedTab"
      fixed-tabs
      height="36px"
      hide-slider
      :show-arrows="xsOnly"
      active-class="tab-navigation__tabs__tab--active"
      class="tab-navigation__tabs"
    >
      <v-tab
        v-for="tab in visibleTabs"
        v-show="visibleTabs.length > 1 && !tab.hideHeader"
        :key="tab.text"
        :to="tab.route"
        class="tab-navigation__tabs__tab"
        :class="getClass(tab.route)"
      >
        <div>{{ tab.text }}</div>
      </v-tab>
      <v-tab-item
        v-for="tab of tabContents"
        :key="tab.route"
        :value="tab.route"
        :class="
          !noContentMargin
            ? 'tab-navigation__tabs__tab-item--content-margin'
            : null
        "
        class="tab-navigation__tabs__tab-item"
      >
        <div v-if="isDev">
          <router-view v-if="isRouterVisible(route.path, tab)" />
        </div>
        <keep-alive v-else>
          <div>
            <router-view v-if="isRouterVisible(route.path, tab)" />
          </div>
        </keep-alive>
      </v-tab-item>
    </v-tabs>
  </v-container>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';
import { useRoute } from '@/composables/router';
import { TabContent, getClass } from '@/types/tabs';
import { checkIfDevelopment } from '@/utils/env-utils';

const props = defineProps({
  tabContents: { required: true, type: Array as PropType<TabContent[]> },
  noContentMargin: { required: false, type: Boolean, default: false }
});

const { tabContents } = toRefs(props);
const selectedTab = ref('');

const route = useRoute();
const { currentBreakpoint } = useTheme();
const isDev = checkIfDevelopment();

const visibleTabs = computed(() => {
  return get(tabContents).filter(({ hidden }) => !hidden);
});

const xsOnly = computed(() => get(currentBreakpoint).xsOnly);

const isRouterVisible = (route: string, tab: TabContent) => {
  return route.indexOf(tab.route) >= 0 && tab.route === get(selectedTab);
};
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
    :deep() {
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
        overflow: visible;
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
