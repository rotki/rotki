<template>
  <v-card>
    <v-stepper v-model="step" vertical>
      <v-stepper-step :complete="step > 1" step="1">
        Setup DeFi
      </v-stepper-step>
      <v-stepper-content step="1">
        <v-card class="mb-12" height="200px" outlined color="grey lighten-4">
          <v-card-subtitle>
            Select options to improve your Rotki DeFi experience
          </v-card-subtitle>
          <v-card-text>
            <p>
              Rotki will attempt by default to retrieve information for all your
              accounts and available modules. The retrieval might require a lot
              of time based on the number of accounts you have.
            </p>
            <p>
              To reduce the fetching time you can specify only the DeFi modules
              and accounts you are interested in.
            </p>
          </v-card-text>
        </v-card>
        <v-btn color="primary" @click="step = 2">Continue</v-btn>
      </v-stepper-content>
      <v-stepper-step :complete="step > 2" step="2">
        Select Modules
      </v-stepper-step>
      <v-stepper-content step="2">
        <v-card outlined color="grey lighten-4" class="mb-12" height="300px">
          <v-card-subtitle>
            Select the modules you would like to activate.
          </v-card-subtitle>
          <v-card-text>
            <v-row>
              <v-col>
                <defi-module-selector v-model="activeModules" />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
        <v-btn text :disabled="loading" @click="step = 1">Back</v-btn>
        <v-btn
          color="primary"
          :disabled="loading"
          :loading="loading"
          @click="modulesSelected()"
        >
          Continue
        </v-btn>
      </v-stepper-content>
      <v-stepper-step :complete="step > 3" step="3">
        Select accounts
      </v-stepper-step>
      <v-stepper-content step="3">
        <v-card outlined color="grey lighten-4" class="mb-12" height="300px">
          <defi-address-selector />
        </v-card>
        <v-btn text @click="step = 2">Back</v-btn>
        <v-btn color="primary" @click="done()">Complete</v-btn>
      </v-stepper-content>
    </v-stepper>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapMutations } from 'vuex';
import DefiAddressSelector from '@/components/defi/wizard/DefiAddressSelector.vue';
import DefiModuleSelector from '@/components/defi/wizard/DefiModuleSelector.vue';
import { SupportedModules } from '@/services/session/types';
import { SettingsUpdate } from '@/typing/types';

@Component({
  components: { DefiAddressSelector, DefiModuleSelector },
  methods: {
    ...mapActions('session', ['updateSettings']),
    ...mapMutations('session', ['defiSetup'])
  }
})
export default class DefiWizard extends Vue {
  updateSettings!: (update: SettingsUpdate) => Promise<void>;
  defiSetup!: (done: boolean) => void;

  loading: boolean = false;
  step: number = 1;
  activeModules: SupportedModules[] = [];

  async modulesSelected() {
    this.loading = true;
    await this.updateSettings({ active_modules: this.activeModules });
    this.loading = false;
    this.step = 3;
  }

  done() {
    this.defiSetup(true);
  }
}
</script>

<style scoped></style>
