<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

withDefaults(
  defineProps<{
    visible: boolean;
    colspan: number;
    noPadding?: boolean;
    offset?: number;
    offsetClassName?: string;
  }>(),
  {
    noPadding: false,
    offset: 0,
    offsetClassName: ''
  }
);
</script>

<template>
  <Fragment>
    <td
      v-if="offset > 0"
      class="table-expand-container table-expand-container__offset"
      :colspan="offset"
      :class="offsetClassName"
    >
      <slot name="offset" />
    </td>
    <td v-if="visible" class="table-expand-container" :colspan="colspan">
      <div class="py-4">
        <div v-if="$scopedSlots.title" class="text-h6 mb-4">
          <slot name="title" />
        </div>
        <template v-if="$scopedSlots.default">
          <RuiCard :no-padding="noPadding">
            <slot />
          </RuiCard>
        </template>
        <div>
          <slot name="append" />
        </div>
      </div>
    </td>
  </Fragment>
</template>

<style scoped lang="scss">
.table-expand-container {
  background-color: var(--v-rotki-light-grey-base) !important;

  @media screen and (max-width: 599px) {
    width: 599px;

    &__offset {
      @apply hidden;
    }
  }
}
</style>
