<template>
  <v-card class="stat-card-wide" :loading="!locked && loading">
    <v-row v-if="!locked" no-gutters>
      <v-col class="stat-card-wide__first-col pa-6" cols="12" :sm="size">
        <slot name="first-col" />
      </v-col>
      <v-col
        class="stat-card-wide__second-col d-flex"
        :class="{
          'stat-card-wide__second-col--horizontal': currentBreakpoint.smAndUp
        }"
        cols="12"
        :sm="size"
      >
        <v-divider :vertical="currentBreakpoint.smAndUp" />
        <div class="stat-card-wide__second-col__content pa-6 flex-grow-1">
          <slot name="second-col" />
        </div>
        <v-divider v-if="cols > 2" :vertical="currentBreakpoint.smAndUp" />
      </v-col>
      <v-col
        v-if="cols > 2"
        class="stat-card-wide__third-col pa-6"
        cols="12"
        :sm="size"
      >
        <slot name="third-col" />
      </v-col>
      <v-col
        v-if="cols > 3"
        class="stat-card-wide__fourth-col pa-6"
        cols="12"
        :sm="size"
      >
        <slot name="fourth-col" />
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col cols="12" class="pa-6 text-right">
        <premium-lock />
      </v-col>
    </v-row>
  </v-card>
</template>

<script setup lang="ts">
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { useTheme } from '@/composables/common';
import { assert } from '@/utils/assertions';

const props = defineProps({
  locked: { required: false, type: Boolean, default: false },
  loading: { required: false, type: Boolean, default: false },
  cols: { required: false, type: Number, default: 3 }
});

const { cols } = toRefs(props);
const colsSize = {
  2: 6,
  3: 4,
  4: 3
};

const { currentBreakpoint } = useTheme();

const size = computed(() => {
  const colNum = get(cols);
  assert(colNum === 2 || colNum === 3 || colNum === 4);
  return colsSize[colNum];
});
</script>

<style scoped lang="scss">
.stat-card-wide {
  &__second-col {
    flex-direction: column;

    &--horizontal {
      flex-direction: row;
    }
  }
}
</style>
