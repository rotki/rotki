<template>
  <v-card>
    <v-stepper v-model="step" vertical>
      <v-stepper-step
        :complete="step > 1"
        step="1"
        v-text="$t('defi_wizard.steps.setup.title')"
      />
      <v-stepper-content step="1">
        <v-card class="mb-12" height="200px" outlined color="grey lighten-4">
          <v-card-title v-text="$t('defi_wizard.steps.setup.subtitle')" />
          <v-card-text>
            <p v-text="$t('defi_wizard.steps.setup.description_line_one')" />
            <p v-text="$t('defi_wizard.steps.setup.description_line_two')" />
            <p v-text="$t('defi_wizard.steps.setup.description_line_three')" />
          </v-card-text>
        </v-card>
        <v-btn
          text
          class="defi-wizard__use-default"
          @click="done"
          v-text="$t('defi_wizard.steps.setup.used_default')"
        />
        <v-btn
          color="primary"
          class="defi-wizard__select-modules"
          @click="step = 2"
          v-text="$t('defi_wizard.steps.setup.continue')"
        />
      </v-stepper-content>
      <v-stepper-step
        :complete="step > 2"
        step="2"
        v-text="$t('defi_wizard.steps.select_modules.title')"
      />
      <v-stepper-content step="2">
        <v-card outlined color="grey lighten-4" class="mb-12" height="300px">
          <v-card-title
            v-text="$t('defi_wizard.steps.select_modules.subtitle')"
          />
          <v-card-subtitle
            v-text="$t('defi_wizard.steps.select_modules.hint')"
          />
          <v-card-text>
            <v-row>
              <v-col>
                <defi-module-selector />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
        <v-btn
          text
          @click="step = 1"
          v-text="$t('defi_wizard.steps.select_modules.back')"
        />
        <v-btn
          color="primary"
          class="defi-wizard__select-accounts"
          @click="step = 3"
          v-text="$t('defi_wizard.steps.select_modules.continue')"
        />
      </v-stepper-content>
      <v-stepper-step
        :complete="step > 3"
        step="3"
        v-text="$t('defi_wizard.steps.select_accounts.title')"
      />
      <v-stepper-content step="3">
        <v-card outlined color="grey lighten-4" class="mb-12" height="400px">
          <v-card-title
            v-text="$t('defi_wizard.steps.select_accounts.subtitle')"
          />
          <v-card-subtitle
            v-text="$t('defi_wizard.steps.select_accounts.hint')"
          />
          <defi-address-selector />
        </v-card>
        <v-btn
          text
          @click="step = 2"
          v-text="$t('defi_wizard.steps.select_accounts.back')"
        />
        <v-btn
          color="primary"
          class="defi-wizard__done"
          @click="done()"
          v-text="$t('defi_wizard.steps.select_accounts.continue')"
        />
      </v-stepper-content>
    </v-stepper>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import DefiAddressSelector from '@/components/defi/wizard/DefiAddressSelector.vue';
import DefiModuleSelector from '@/components/defi/wizard/DefiModuleSelector.vue';
import { DEFI_SETUP_DONE } from '@/store/settings/consts';
import { FrontendSettingsPayload } from '@/store/settings/types';

@Component({
  components: { DefiAddressSelector, DefiModuleSelector },
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

<style scoped></style>
