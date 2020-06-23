<template>
  <v-tabs
    fixed-tabs
    height="36px"
    hide-slider
    active-class="tab-navigation__tabs__tab--active"
    class="tab-navigation__tabs py-6"
  >
    <v-tab
      v-for="tab in tabContents"
      :key="tab.name"
      :to="tab.routerTo"
      class="tab-navigation__tabs__tab"
      :class="tab.routerTo.toLowerCase().replace('/', '').replace(/\//g, '__')"
    >
      {{ tab.name }}
    </v-tab>
  </v-tabs>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';

export interface TabContent {
  name: string;
  routerTo: string;
}

@Component({})
export default class TabNavigation extends Vue {
  @Prop({ required: true, type: Array })
  tabContents!: TabContent[];
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
    &__tab {
      border: 1px solid #7e4a3b;

      &--active {
        background-color: #7e4a3b;
        color: #fff;
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
