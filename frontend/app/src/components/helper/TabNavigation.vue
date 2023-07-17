<script setup lang="ts">
import { type PropType } from 'vue';
import { type TabContent, getClass } from '@/types/tabs';

const props = defineProps({
  tabContents: { required: true, type: Array as PropType<TabContent[]> },
  noContentMargin: { required: false, type: Boolean, default: false }
});

const { tabContents } = toRefs(props);
const selectedTab = ref('');

const route = useRoute();
const { xs } = useDisplay();
const isDev = checkIfDevelopment();

const visibleTabs = computed(() =>
  get(tabContents).filter(({ hidden }) => !hidden)
);

const isRouterVisible = (route: string, tab: TabContent) =>
  route.includes(tab.route) && tab.route === get(selectedTab);
</script>

<template>
  <VContainer>
    <VTabs
      v-model="selectedTab"
      fixed-tabs
      height="36px"
      hide-slider
      :show-arrows="xs"
      active-class="tab-navigation__tabs__tab--active"
      class="tab-navigation__tabs"
    >
      <VTab
        v-for="tab in visibleTabs"
        v-show="visibleTabs.length > 1 && !tab.hideHeader"
        :key="tab.text"
        :to="tab.route"
        class="tab-navigation__tabs__tab"
        :class="getClass(tab.route)"
      >
        <div>{{ tab.text }}</div>
      </VTab>
      <VTabItem
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
          <RouterView v-if="isRouterVisible(route.path, tab)" />
        </div>
        <KeepAlive v-else>
          <div>
            <RouterView v-if="isRouterVisible(route.path, tab)" />
          </div>
        </KeepAlive>
      </VTabItem>
    </VTabs>
  </VContainer>
</template>

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
    &__tab-item {
      &--content-margin {
        margin-top: 36px;
      }
    }

    &__tab {
      text-transform: uppercase;
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

      /* stylelint-disable no-descending-specificity */

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

:deep(.v-tabs) {
  .v-tabs {
    &-bar {
      background: transparent !important;
    }

    &-items {
      background-color: transparent !important;
      overflow: visible;
    }
  }
}

.theme {
  &--dark {
    .tab-navigation {
      &__tabs {
        &__tab {
          &:not(&--active) {
            /* stylelint-enable no-descending-specificity */
            background: var(--v-dark-base) !important;
          }
        }
      }
    }
  }
}
</style>
