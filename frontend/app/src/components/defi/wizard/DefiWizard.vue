<template>
  <v-card>
    <v-stepper v-model="step" vertical>
      <v-stepper-step :complete="step > 1" step="1">
        {{ $t('defi_wizard.steps.setup.title') }}
      </v-stepper-step>
      <v-stepper-content step="1">
        <card class="mb-12" outlined>
          <template #title>
            {{ $t('defi_wizard.steps.setup.subtitle') }}
          </template>
          <p>
            {{ $t('defi_wizard.steps.setup.description_line_one') }}
          </p>
          <p>
            {{ $t('defi_wizard.steps.setup.description_line_two') }}
          </p>
          <p>
            {{ $t('defi_wizard.steps.setup.description_line_three') }}
          </p>
        </card>
        <v-btn text class="defi-wizard__use-default" @click="done">
          {{ $t('defi_wizard.steps.setup.used_default') }}
        </v-btn>
        <v-btn
          color="primary"
          class="defi-wizard__select-modules"
          @click="step = 2"
        >
          {{ $t('defi_wizard.steps.setup.continue') }}
        </v-btn>
      </v-stepper-content>
      <v-stepper-step :complete="step > 2" step="2">
        {{ $t('defi_wizard.steps.select_modules.title') }}
      </v-stepper-step>
      <v-stepper-content step="2">
        <card outlined class="mb-12">
          <template #title>
            {{ $t('defi_wizard.steps.select_modules.subtitle') }}
          </template>
          <template #subtitle>
            {{ $t('defi_wizard.steps.select_modules.hint') }}
          </template>
          <v-row>
            <v-col>
              <module-selector />
            </v-col>
          </v-row>
        </card>
        <v-btn text @click="step = 1">
          {{ $t('defi_wizard.steps.select_modules.back') }}
        </v-btn>
        <v-btn
          color="primary"
          class="defi-wizard__select-accounts"
          @click="step = 3"
        >
          {{ $t('defi_wizard.steps.select_modules.continue') }}
        </v-btn>
      </v-stepper-content>
      <v-stepper-step :complete="step > 3" step="3">
        {{ $t('defi_wizard.steps.select_accounts.title') }}
      </v-stepper-step>
      <v-stepper-content step="3">
        <card outlined class="mb-12">
          <template #title>
            {{ $t('defi_wizard.steps.select_accounts.subtitle') }}
          </template>
          <template #subtitle>
            {{ $t('defi_wizard.steps.select_accounts.hint') }}
          </template>
          <module-address-selector class="defi-wizard__address-selector" />
        </card>
        <v-btn text @click="step = 2">
          {{ $t('defi_wizard.steps.select_accounts.back') }}
        </v-btn>
        <v-btn color="primary" class="defi-wizard__done" @click="done()">
          {{ $t('defi_wizard.steps.select_accounts.continue') }}
        </v-btn>
      </v-stepper-content>
    </v-stepper>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ModuleAddressSelector from '@/components/defi/wizard/ModuleAddressSelector.vue';
import ModuleSelector from '@/components/defi/wizard/ModuleSelector.vue';
import { DEFI_SETUP_DONE } from '@/store/settings/consts';
import { FrontendSettingsPayload } from '@/store/settings/types';

@Component({
  components: { ModuleAddressSelector, ModuleSelector },
  methods: {
    ...mapActions('settings', ['updateSetting'])
  }
})
export default class DefiWizard extends Vue {
  updateSetting!: (payload: FrontendSettingsPayload) => void;

  step: number = 1;
  done() {
    this.updateSetting({ [DEFI_SETUP_DONE]: true });
  }
}
</script>

<style scoped lang="scss">
.defi-wizard {
  &__address-selector {
    ::v-deep {
      .v-stepper {
        &__content {
          margin: auto !important;
          border-left: none !important;
        }
      }
    }
  }
}
</style>
