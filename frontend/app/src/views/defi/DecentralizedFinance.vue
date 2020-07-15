<template>
  <v-container>
    <v-row>
      <v-col>
        <h1>Decentralized Finance</h1>
        <tab-navigation :tab-contents="tabs"></tab-navigation>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';

@Component({
  components: { TabNavigation }
})
export default class DecentralizedFinance extends Vue {
  readonly tabs: TabContent[] = [
    {
      name: 'Overview',
      routeTo: '/defi/overview'
    },
    {
      name: 'Lending',
      routeTo: '/defi/lending'
    },
    {
      name: 'Borrowing',
      routeTo: '/defi/borrowing'
    }
  ];
}
</script>

<style scoped></style>
