<template>
  <v-card>
    <v-stepper v-model="step" vertical>
      <v-stepper-step :complete="step > 1" step="1">
        Setup DeFi
      </v-stepper-step>
      <v-stepper-content step="1">
        <v-card class="mb-12" height="200px" outlined color="grey lighten-4">
          <v-card-title>
            Select options to improve your rotki DeFi experience
          </v-card-title>
          <v-card-text>
            <p>
              rotki will attempt by default to retrieve information for all your
              accounts and available modules. The retrieval might require a lot
              of time based on the number of accounts you have.
            </p>
            <p>
              To reduce the query time you can specify only the DeFi modules and
              accounts you are interested in.
            </p>
            <p>
              You can use the default settings if you want to have information
              for all protocols fetched for all accounts automatically. (Defi
              Settings can be changed at a later time).
            </p>
          </v-card-text>
        </v-card>
        <v-btn text @click="done">Use Default</v-btn>
        <v-btn color="primary" @click="step = 2">Continue</v-btn>
      </v-stepper-content>
      <v-stepper-step :complete="step > 2" step="2">
        Select Modules
      </v-stepper-step>
      <v-stepper-content step="2">
        <v-card outlined color="grey lighten-4" class="mb-12" height="300px">
          <v-card-title>
            Select the modules you would like to activate.
          </v-card-title>
          <v-card-subtitle>
            If no modules are specified, querying for the supported modules will
            be disabled.
          </v-card-subtitle>
          <v-card-text>
            <v-row>
              <v-col>
                <defi-module-selector />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
        <v-btn text @click="step = 1">Back</v-btn>
        <v-btn color="primary" @click="modulesSelected()">
          Continue
        </v-btn>
      </v-stepper-content>
      <v-stepper-step :complete="step > 3" step="3">
        Select accounts
      </v-stepper-step>
      <v-stepper-content step="3">
        <v-card outlined color="grey lighten-4" class="mb-12" height="400px">
          <v-card-title>Select accounts</v-card-title>
          <v-card-subtitle>
            Select accounts for which data will be retrieved for each submodule.
            If no addresses are selected data will be retrieved for all
            available addresses
          </v-card-subtitle>
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
import { mapActions } from 'vuex';
import DefiAddressSelector from '@/components/defi/wizard/DefiAddressSelector.vue';
import DefiModuleSelector from '@/components/defi/wizard/DefiModuleSelector.vue';

@Component({
  components: { DefiAddressSelector, DefiModuleSelector },
  methods: {
    ...mapActions('session', ['defiSetupDone'])
  }
})
export default class DefiWizard extends Vue {
  defiSetupDone!: (done: boolean) => void;

  step: number = 1;

  async modulesSelected() {
    this.step = 3;
  }

  done() {
    this.defiSetupDone(true);
  }
}
</script>

<style scoped></style>
