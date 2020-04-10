<template>
  <v-card>
    <v-card-title>Manually Tracked Balances</v-card-title>
    <v-card-text>
      <manually-tracked-form></manually-tracked-form>
      <h3 class="text-center">Balances</h3>
      <manually-tracked-balance-list></manually-tracked-balance-list>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ManuallyTrackedBalanceList from '@/components/accounts/ManuallyTrackedBalanceList.vue';
import ManuallyTrackedForm from '@/components/accounts/ManuallyTrackedForm.vue';

@Component({
  components: { ManuallyTrackedBalanceList, ManuallyTrackedForm }
})
export default class ManuallyTrackedBalances extends Vue {
  async mounted() {
    await this.$store.dispatch('balances/fetchSupportedAssets');
    await this.$store.dispatch('balances/fetchManualBalances');
  }
}
</script>

<style scoped></style>
