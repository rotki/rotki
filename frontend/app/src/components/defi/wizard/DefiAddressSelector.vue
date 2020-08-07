<template>
  <v-stepper v-model="step" class="defi-address-selector">
    <v-stepper-header>
      <template v-for="n in steps">
        <v-stepper-step
          :key="`${n}-step`"
          :complete="step > n"
          :step="n"
          editable
        >
          <span class="d-flex flex-column align-center justify-center">
            <v-img
              width="55px"
              contain
              max-height="24px"
              :src="modules[n - 1].icon"
            />
            <span v-if="modules[n - 1].name">
              {{ modules[n - 1].name }}
            </span>
          </span>
        </v-stepper-step>

        <v-divider v-if="n !== steps" :key="n"></v-divider>
      </template>
    </v-stepper-header>

    <v-stepper-items>
      <v-stepper-content v-for="n in steps" :key="`${n}-content`" :step="n">
        <v-card class="mb-12" flat height="110px">
          <defi-queriable-address
            :module="modules[n - 1].identifier"
            :selected-addresses="
              queriedAddresses[modules[n - 1].identifier]
                ? queriedAddresses[modules[n - 1].identifier]
                : []
            "
          />
        </v-card>

        <v-btn v-if="step > 1" text @click="previousStep(n)">Back</v-btn>
        <v-btn
          v-if="step < modules.length"
          color="primary"
          @click="nextStep(n)"
        >
          Next
        </v-btn>
      </v-stepper-content>
    </v-stepper-items>
  </v-stepper>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import { DEFI_MODULES } from '@/components/defi/wizard/consts';
import DefiQueriableAddress from '@/components/defi/wizard/DefiQueriableAddress.vue';
import { Module } from '@/components/defi/wizard/types';
import { QueriedAddresses, SupportedModules } from '@/services/session/types';

@Component({
  components: { DefiQueriableAddress },
  computed: {
    ...mapGetters('session', ['activeModules']),
    ...mapState('session', ['queriedAddresses'])
  },
  methods: {
    ...mapActions('session', ['fetchQueriedAddresses'])
  }
})
export default class DefiAddressSelector extends Vue {
  step: number = 1;
  activeModules!: SupportedModules[];
  queriedAddresses!: QueriedAddresses;
  fetchQueriedAddresses!: () => Promise<void>;

  async mounted() {
    await this.fetchQueriedAddresses();
  }

  get modules(): Module[] {
    if (this.activeModules.length === 0) {
      return DEFI_MODULES;
    }
    return DEFI_MODULES.filter(module =>
      this.activeModules.includes(module.identifier)
    );
  }

  get steps(): number {
    return this.modules.length;
  }
  nextStep(step: number) {
    this.step = step + 1;
  }

  previousStep(step: number) {
    this.step = step - 1;
  }
}
</script>

<style scoped lang="scss">
.defi-address-selector {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;

  ::v-deep {
    .v-stepper {
      &__header {
        border: none !important;
        box-shadow: none !important;
      }
    }
  }
}
</style>
