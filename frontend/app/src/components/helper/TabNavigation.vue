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
      v-for="tab in tabContents"
      :key="tab.name"
      :to="tab.routeTo"
      class="tab-navigation__tabs__tab"
      :class="tab.routeTo.toLowerCase().replace('/', '').replace(/\//g, '__')"
    >
      {{ tab.name }}
    </v-tab>
    <v-tab-item
      v-for="tab of tabContents"
      :key="tab.id"
      :value="tab.routeTo"
      class="tab-navigation__tabs__tab-item"
    >
      <router-view v-if="tab.routeTo === selectedTab"></router-view>
    </v-tab-item>
  </v-tabs>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

export interface TabContent {
  name: string;
  routeTo: string;
}

@Component({})
export default class TabNavigation extends Vue {
  @Prop({ required: true, type: Array })
  tabContents!: TabContent[];
  selectedTab: string = '';
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

      .v-tabs-items {
        background-color: transparent !important;
      }
    }

    &__tab-item {
      margin-top: 50px;
    }

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
        color: white;
        background-color: var(--v-primary-base) !important;
      }

      &:first-of-type {
        &:hover {
          @include start();
        }

        @include start();
      }
      /* stylelint-disable no-descending-specificity */

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
