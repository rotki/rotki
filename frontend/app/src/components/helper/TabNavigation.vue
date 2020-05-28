<template>
  <v-tabs
    fixed-tabs
    height="36px"
    hide-slider
    active-class="tab-navigation__tab--active"
    class="tab-navigation__tab py-6"
  >
    <v-tab
      v-for="tab in tabContents"
      :key="tab.name"
      :to="tab.routerTo"
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
.tab-navigation {
  &__tab {
    &--active {
      background-color: #7e4a3b;
      color: #fff;
    }
    & a {
      border: 1px solid #7e4a3b;
    }

    a:first-of-type,
    a:first-of-type:hover {
      border-radius: 8px 0 0 8px;
      border-right: 0;
    }

    a:last-of-type,
    a:last-of-type:hover {
      border-radius: 0 8px 8px 0;
      border-left: 0;
    }

    .v-tab:hover::before {
      border-radius: inherit;
    }
  }
}
</style>
