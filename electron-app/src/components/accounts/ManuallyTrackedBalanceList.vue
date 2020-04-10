<template>
  <v-data-table :headers="headers" :items="manualBalances"> </v-data-table>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { ManualBalance } from '@/services/types-model';

const { mapState } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapState(['manualBalances'])
  }
})
export default class ManuallyTrackedBalanceList extends Vue {
  headers = [
    { text: 'Label', value: 'label' },
    { text: 'Asset', value: 'asset', width: '200' },
    { text: 'Amount', value: 'amount' },
    { text: 'USD Value', value: 'usdValue' },
    { text: 'Location', value: 'location' },
    { text: 'Actions', value: 'actions', sortable: false, width: '50' }
  ];

  manualBalances!: ManualBalance[];
}
</script>

<style scoped lang="scss"></style>
