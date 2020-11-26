<template>
  <v-container
    :style="`height: calc(100vh - ${top + 64}px);`"
    class="d-flex flex-column align-center justify-center"
  >
    <div class="module-not-active__container">
      <v-row align="center" justify="center">
        <v-col cols="auto">
          <v-img
            max-width="82px"
            contain
            :src="require('@/assets/images/defi/uniswap.svg')"
          />
        </v-col>
      </v-row>
      <v-divider class="mt-12" />
      <v-row align="center" justify="center">
        <v-col cols="auto" class="text--secondary">
          <i18n tag="span" path="module_not_active.not_active">
            <template #link>
              <v-btn
                class="module-not-active__link"
                text
                to="/settings/defi"
                small
              >
                {{ $t('module_not_active.settings_link') }}
              </v-btn>
            </template>
            <template #module>
              {{ moduleName }}
            </template>
          </i18n>
        </v-col>
      </v-row>
    </div>
  </v-container>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { MODULES } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';

@Component({})
export default class ModuleNotActive extends Vue {
  @Prop({
    required: true,
    type: String,
    validator: (value: any) => MODULES.includes(value)
  })
  module!: SupportedModules;

  get moduleName(): string {
    return 'Uniswap';
  }

  top: number = 0;

  mounted() {
    const { top } = this.$el.getBoundingClientRect();
    this.top = top;
  }
}
</script>

<style scoped lang="scss">
.module-not-active {
  &__link {
    text-transform: none !important;
  }

  &__container {
    width: 100%;
  }
}
</style>
