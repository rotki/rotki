<template>
  <v-card>
    <v-card-title>Manually Tracked Balances</v-card-title>
    <v-card-text>
      <manual-balances-form
        :edit="edit"
        @clear="edit = null"
      ></manual-balances-form>
      <h3 class="text-center">Balances</h3>
      <manual-balances-list @edit="edit = $event"></manual-balances-list>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ManualBalancesForm from '@/components/accounts/ManualBalancesForm.vue';
import ManualBalancesList from '@/components/accounts/ManualBalancesList.vue';
import { ManualBalance } from '@/services/types-model';

@Component({
  components: { ManualBalancesList, ManualBalancesForm }
})
export default class ManuallyTrackedBalances extends Vue {
  edit: ManualBalance | null = null;

  async mounted() {
    await this.$store.dispatch('balances/fetchSupportedAssets');
    await this.$store.dispatch('balances/fetchManualBalances');
  }
}
</script>

<style scoped></style>
