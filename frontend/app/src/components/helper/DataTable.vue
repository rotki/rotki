<template>
  <v-data-table
    ref="table"
    v-bind="$attrs"
    must-sort
    :sort-desc="sortDesc"
    :items="items"
    :item-class="itemClass"
    :headers="headers"
    :expanded="expanded"
    :footer-props="footerProps"
    :items-per-page="itemsPerPage"
    v-on="$listeners"
    @update:items-per-page="onItemsPerPageChange($event)"
    @update:page="scrollToTop"
  >
    <!-- Pass on all named slots -->
    <slot v-for="slot in Object.keys($slots)" :slot="slot" :name="slot" />
    <!-- Pass on all scoped slots -->
    <template
      v-for="slot in Object.keys($scopedSlots)"
      :slot="slot"
      slot-scope="scope"
    >
      <slot :name="slot" v-bind="scope" />
    </template>

    <template #top="{ pagination, options, updateOptions }">
      <v-data-footer
        v-bind="footerProps"
        :pagination="pagination"
        :options="options"
        @update:options="updateOptions"
      />
      <v-divider />
    </template>
  </v-data-table>
</template>

<script lang="ts">
import { defineComponent, PropType, ref } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import { setupThemeCheck } from '@/composables/common';
import { setupSettings } from '@/composables/settings';
import { footerProps } from '@/config/datatable.common';
import { ITEMS_PER_PAGE } from '@/types/frontend-settings';

export default defineComponent({
  name: 'DataTable',
  props: {
    sortDesc: { required: false, type: Boolean, default: true },
    items: { required: true, type: Array },
    headers: { required: true, type: Array as PropType<DataTableHeader[]> },
    expanded: { required: false, type: Array, default: () => [] },
    itemClass: { required: false, type: [String, Function], default: () => '' }
  },
  setup() {
    const { itemsPerPage, updateSetting } = setupSettings();
    const { $vuetify } = setupThemeCheck();

    const table = ref<any>(null);

    const onItemsPerPageChange = async (newValue: number) => {
      await updateSetting({
        [ITEMS_PER_PAGE]: newValue
      });
    };

    const scrollToTop = () => {
      const tableRef = table.value;
      $vuetify.goTo(tableRef, {
        container: document.querySelector('.app-main') as HTMLElement
      });
    };

    return {
      table,
      itemsPerPage,
      footerProps,
      onItemsPerPageChange,
      scrollToTop
    };
  }
});
</script>

<style scoped lang="scss">
/* stylelint-disable selector-class-pattern,selector-nested-pattern */

.v-data-table--mobile {
  ::v-deep {
    .v-data-table__wrapper {
      tbody {
        .v-data-table__expanded__content,
        .table-expand-container {
          height: auto !important;
          display: block;
        }
      }
    }
  }
}
/* stylelint-enable selector-class-pattern,selector-nested-pattern */
</style>
