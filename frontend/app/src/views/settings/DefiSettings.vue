<template>
  <v-container>
    <v-card>
      <v-card-title v-text="$t('defi_settings.title')" />
      <v-card-text>
        <div class="title" v-text="$t('defi_settings.active_modules')" />
        <p
          class="text--secondary"
          v-text="$t('defi_settings.active_modules_description')"
        />
        <defi-module-selector />
        <div class="mt-6 title" v-text="$t('defi_settings.select_accounts')" />
        <p
          class="text--secondary"
          v-text="$t('defi_settings.select_accounts_description')"
        />
        <defi-address-selector />
        <span class="caption" v-text="$t('defi_settings.hint')" />
      </v-card-text>
    </v-card>
  </v-container>
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
