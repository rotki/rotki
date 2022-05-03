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
    :hide-default-footer="hideDefaultFooter"
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

    <template
      v-if="!hideDefaultFooter"
      #top="{ pagination, options, updateOptions }"
    >
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
import { get, useElementBounding } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
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
    itemClass: { required: false, type: [String, Function], default: () => '' },
    hideDefaultFooter: { required: false, type: Boolean, default: false }
  },
  setup() {
    const { itemsPerPage, updateSetting } = setupSettings();

    const table = ref<any>(null);

    const onItemsPerPageChange = async (newValue: number) => {
      await updateSetting({
        [ITEMS_PER_PAGE]: newValue
      });
    };

    const { top } = useElementBounding(table);

    const scrollToTop = () => {
      const body = document.body;
      if (get(table)) {
        body.scrollTop = get(top) + body.scrollTop - 64;
      }
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
/* stylelint-disable selector-class-pattern,selector-nested-pattern,no-descending-specificity */

::v-deep {
  .v-data-table {
    &__expanded {
      &__content {
        background-color: var(--v-rotki-light-grey-base) !important;
        box-shadow: none !important;
      }
    }

    &--mobile {
      .v-data-table {
        &__wrapper {
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
  }
}

.theme {
  &--dark {
    ::v-deep {
      .v-data-table {
        &__expanded {
          &__content {
            background-color: var(--v-dark-lighten1) !important;
          }
        }
      }
    }
  }
}
/* stylelint-enable selector-class-pattern,selector-nested-pattern,no-descending-specificity */
</style>
