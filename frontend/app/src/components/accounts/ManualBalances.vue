<template>
  <v-card>
    <v-card-title>Manually Tracked Balances</v-card-title>
    <v-card-text>
      <manual-balances-form></manual-balances-form>
      <h3 class="text-center">Balances</h3>
      <manual-balances-list></manual-balances-list>
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
export default class ManualBalances extends Vue {
  edit: ManualBalance | null = null;
}
</script>

<style scoped></style>
