<template>
  <v-container>
    <v-card>
      <v-card-title>
        <card-title> {{ $t('defi_settings.title') }} </card-title>
      </v-card-title>
      <v-card-text>
        <div class="text-h6" v-text="$t('defi_settings.active_modules')" />
        <p
          class="text--secondary"
          v-text="$t('defi_settings.active_modules_description')"
        />
        <defi-module-selector />
        <div
          class="mt-6 text-h6"
          v-text="$t('defi_settings.select_accounts')"
        />
        <p
          class="text--secondary"
          v-text="$t('defi_settings.select_accounts_description')"
        />
        <defi-address-selector />
        <span class="text-caption" v-text="$t('defi_settings.hint')" />
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
