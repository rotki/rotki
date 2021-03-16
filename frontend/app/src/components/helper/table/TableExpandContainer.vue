<template>
  <td
    v-if="visible"
    class="table-expand-container"
    :colspan="$vuetify.breakpoint.xsOnly ? 2 : colspan"
  >
    <div class="py-4">
      <div class="text-h6 mb-4">
        <slot name="title" />
      </div>
      <v-sheet outlined rounded class="pa-4">
        <slot />
      </v-sheet>
    </div>
  </td>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class TableExpandContainer extends Vue {
  @Prop({ required: true, type: Boolean })
  visible!: boolean;
  @Prop({ required: true, type: Number })
  colspan!: number;
}
</script>

<style scoped lang="scss">
.table-expand-container {
  background-color: var(--v-rotki-light-grey-base) !important;
}
</style>
