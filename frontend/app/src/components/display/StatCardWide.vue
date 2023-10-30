<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    locked?: boolean;
    loading?: boolean;
    cols?: number;
  }>(),
  {
    locked: false,
    loading: false,
    cols: 3
  }
);

const { cols } = toRefs(props);
const colsSize = {
  2: 6,
  3: 4,
  4: 3
};

const { smAndUp } = useDisplay();

const size = computed(() => {
  const cols = props.cols;
  assert(cols === 2 || cols === 3 || cols === 4);
  return colsSize[cols];
});
</script>

<template>
  <VCard class="stat-card-wide" :loading="!locked && loading">
    <VRow v-if="!locked" no-gutters>
      <VCol class="stat-card-wide__first-col pa-6" cols="12" :sm="size">
        <slot name="first-col" />
      </VCol>
      <VCol
        class="stat-card-wide__second-col flex"
        :class="{
          'stat-card-wide__second-col--horizontal': smAndUp
        }"
        cols="12"
        :sm="size"
      >
        <VDivider :vertical="smAndUp" />
        <div class="stat-card-wide__second-col__content pa-6 grow">
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
