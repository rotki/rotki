<template>
  <fragment>
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
        <v-sheet
          v-if="$scopedSlots.default"
          outlined
          rounded
          :class="padded ? 'pa-4' : null"
        >
          <slot />
        </v-sheet>
        <div>
          <slot name="append" />
        </div>
      </div>
    </td>
  </fragment>
</template>

<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

defineProps({
  visible: { required: true, type: Boolean },
  colspan: { required: true, type: Number },
  padded: { required: false, type: Boolean, default: true },
  offset: { required: false, type: Number, default: 0 },
  offsetClassName: { required: false, type: String, default: '' }
});
</script>

<style scoped lang="scss">
.table-expand-container {
  background-color: var(--v-rotki-light-grey-base) !important;

  @media screen and (max-width: 599px) {
    width: 599px;

    &__offset {
      display: none;
    }
  }
}
</style>
