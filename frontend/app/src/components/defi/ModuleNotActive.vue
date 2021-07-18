<template>
  <v-container
    :style="`height: calc(100vh - ${top + 64}px);`"
    class="d-flex flex-column align-center justify-center"
  >
    <div class="module-not-active__container">
      <v-row align="center" justify="center">
        <v-col v-for="module in modules" :key="module" cols="auto">
          <v-img width="82px" contain :src="icon(module)" />
        </v-col>
      </v-row>
      <v-row align="center" justify="center" class="mt-16">
        <v-col cols="auto" class="text--secondary">
          <i18n
            tag="span"
            path="module_not_active.not_active"
            class="text-center"
          >
            <template #link>
              <router-link
                class="module-not-active__link font-weight-regular text-body-1 text-decoration-none"
                text
                to="/settings/modules"
                small
              >
                {{ $t('module_not_active.settings_link') }}
              </router-link>
            </template>
            <template #text>
              <div v-if="modules.length > 1">
                {{ $t('module_not_active.at_least_one') }}
              </div>
            </template>
            <template #module>
              <span
                v-for="module in modules"
                :key="`mod-${module}`"
                class="module-not-active__module"
              >
                {{ name(module) }}
              </span>
            </template>
          </i18n>
        </v-col>
      </v-row>
    </div>
  </v-container>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import { MODULES } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';

@Component({})
export default class ModuleNotActive extends Vue {
  @Prop({
    required: true,
    type: Array,
    validator: (value: SupportedModules[]) =>
      value.every(module => MODULES.includes(module))
  })
  modules!: SupportedModules;

  name(module: string): string {
    const data = SUPPORTED_MODULES.find(value => value.identifier === module);
    return data?.name ?? '';
  }

  icon(module: SupportedModules): string {
    const data = SUPPORTED_MODULES.find(value => value.identifier === module);
    return data?.icon ?? '';
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

  &__module {
    &:not(:first-child) {
      &:before {
        content: '& ';
      }
    }
  }
}
</style>
