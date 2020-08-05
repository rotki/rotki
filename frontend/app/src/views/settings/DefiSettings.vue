<template>
  <v-card>
    <v-card-title>Defi Settings</v-card-title>
    <v-card-text>
      <h3>Active Defi modules</h3>
      <p class="text--secondary">
        Only data for the selected modules will be fetched. If no modules are
        selected data for all the modules will by fetched.
      </p>
      <defi-module-selector />
      <h3 class="mt-6">Selected accounts</h3>
      <p class="text--secondary">
        Only data for the selected accounts will be fetched. If no accounts are
        selected all data will be fetched.
      </p>
      <defi-address-selector />
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import DefiAddressSelector from '@/components/defi/wizard/DefiAddressSelector.vue';
import DefiModuleSelector from '@/components/defi/wizard/DefiModuleSelector.vue';

@Component({
  components: { DefiAddressSelector, DefiModuleSelector }
})
export default class DefiSettings extends Vue {}
</script>

<style scoped></style>
