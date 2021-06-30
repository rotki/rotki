<template>
  <v-container>
    <v-card>
      <v-card-title>
        <card-title> {{ $t('module_settings.title') }} </card-title>
      </v-card-title>
      <v-card-text>
        <div class="text-h6" v-text="$t('module_settings.active_modules')" />
        <p
          class="text--secondary"
          v-text="$t('module_settings.active_modules_description')"
        />
        <module-selector />
        <div
          class="mt-6 text-h6"
          v-text="$t('module_settings.select_accounts')"
        />
        <p
          class="text--secondary"
          v-text="$t('module_settings.select_accounts_description')"
        />
        <module-address-selector />
        <span class="text-caption" v-text="$t('module_settings.hint')" />
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ModuleAddressSelector from '@/components/defi/wizard/ModuleAddressSelector.vue';
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';

@Component({
  components: { ModuleSelector, ModuleAddressSelector }
})
export default class ModuleSettings extends Vue {}
</script>
