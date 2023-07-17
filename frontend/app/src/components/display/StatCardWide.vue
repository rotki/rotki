<script setup lang="ts">
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

const { smAndUp } = useDisplay();

const size = computed(() => {
  const colNum = get(cols);
  assert(colNum === 2 || colNum === 3 || colNum === 4);
  return colsSize[colNum];
});
</script>

<template>
  <VCard class="stat-card-wide" :loading="!locked && loading">
    <VRow v-if="!locked" no-gutters>
      <VCol class="stat-card-wide__first-col pa-6" cols="12" :sm="size">
        <slot name="first-col" />
      </VCol>
      <VCol
        class="stat-card-wide__second-col d-flex"
        :class="{
          'stat-card-wide__second-col--horizontal': smAndUp
        }"
        cols="12"
        :sm="size"
      >
        <VDivider :vertical="smAndUp" />
        <div class="stat-card-wide__second-col__content pa-6 flex-grow-1">
          <slot name="second-col" />
        </div>
        <VDivider v-if="cols > 2" :vertical="smAndUp" />
      </VCol>
      <VCol
        v-if="cols > 2"
        class="stat-card-wide__third-col pa-6"
        cols="12"
        :sm="size"
      >
        <slot name="third-col" />
      </VCol>
      <VCol
        v-if="cols > 3"
        class="stat-card-wide__fourth-col pa-6"
        cols="12"
        :sm="size"
      >
        <slot name="fourth-col" />
      </VCol>
    </VRow>
    <VRow v-else>
      <VCol cols="12" class="pa-6 text-right">
        <PremiumLock />
      </VCol>
    </VRow>
  </VCard>
</template>

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
