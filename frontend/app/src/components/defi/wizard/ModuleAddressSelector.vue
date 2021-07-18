<template>
  <v-stepper v-model="step" class="module-address-selector">
    <v-sheet rounded outlined>
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
              <span v-if="modules[n - 1].name" class="mt-3 text-center">
                {{ modules[n - 1].name }}
              </span>
            </span>
          </v-stepper-step>

          <v-divider v-if="n !== steps" :key="n" />
        </template>
      </v-stepper-header>
    </v-sheet>

    <v-stepper-items>
      <v-stepper-content v-for="n in steps" :key="`${n}-content`" :step="n">
        <v-row align="center">
          <v-col cols="auto">
            <v-img
              width="30px"
              contain
              max-height="24px"
              :src="modules[n - 1].icon"
            />
          </v-col>
          <v-col>
            <div class="text-h6">{{ modules[n - 1].name }}</div>
          </v-col>
        </v-row>

        <v-card class="mb-12 mt-4" flat height="110px">
          <module-queried-address
            :module="modules[n - 1].identifier"
            :selected-addresses="
              queriedAddresses[modules[n - 1].identifier]
                ? queriedAddresses[modules[n - 1].identifier]
                : []
            "
          />
        </v-card>

        <v-btn v-if="step > 1" text @click="previousStep(n)">
          {{ $t('module_address_selector.back') }}
        </v-btn>
        <v-btn
          v-if="step < modules.length"
          color="primary"
          @click="nextStep(n)"
        >
          {{ $t('module_address_selector.next') }}
        </v-btn>
      </v-stepper-content>
    </v-stepper-items>
  </v-stepper>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import ModuleQueriedAddress from '@/components/defi/wizard/ModuleQueriedAddress.vue';
import { Module } from '@/components/defi/wizard/types';
import { QueriedAddresses, SupportedModules } from '@/services/session/types';

@Component({
  components: { ModuleQueriedAddress },
  computed: {
    ...mapGetters('session', ['activeModules']),
    ...mapState('session', ['queriedAddresses'])
  },
  methods: {
    ...mapActions('session', ['fetchQueriedAddresses'])
  }
})
export default class ModuleAddressSelector extends Vue {
  step: number = 1;
  activeModules!: SupportedModules[];
  queriedAddresses!: QueriedAddresses;
  fetchQueriedAddresses!: () => Promise<void>;

  async mounted() {
    await this.fetchQueriedAddresses();
  }

  get modules(): Module[] {
    if (this.activeModules.length === 0) {
      return SUPPORTED_MODULES;
    }
    return SUPPORTED_MODULES.filter(module =>
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

<!--suppress Stylelint -->
<style scoped lang="scss">
@import '~@/scss/scroll';

.module-address-selector {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;

  ::v-deep {
    .v-stepper {
      &__header {
        border: none !important;
        box-shadow: none !important;
        overflow-x: auto;
        height: 120px;
        flex-wrap: nowrap;

        @extend .themed-scrollbar;
      }

      &__step {
        &__step {
          display: none !important;
        }
      }

      &__label {
        min-width: 112px;
        display: block;
      }

      &__items {
        margin-top: 24px;
        border-radius: 4px;
        border: thin solid rgba(0, 0, 0, 0.12);
      }

      /* stylelint-disable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
      .theme--dark &__items {
        border: thin solid rgba(255, 255, 255, 0.12);
      }
      /* stylelint-enable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
    }
  }
}
</style>
