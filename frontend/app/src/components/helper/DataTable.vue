<template>
  <v-data-table
    ref="tableRef"
    v-bind="rootAttrs"
    :must-sort="mustSort"
    :sort-desc="sortDesc"
    :items="items"
    :item-class="itemClass"
    :headers="headers"
    :expanded="expanded"
    :footer-props="footerProps"
    :page.sync="currentPage"
    :items-per-page="itemsPerPage"
    :hide-default-footer="hideDefaultFooter"
    :loading="loading"
    :loading-text="loadingText"
    v-on="rootListeners"
    @update:items-per-page="onItemsPerPageChange($event)"
    @update:page="scrollToTop"
  >
    <!-- Pass on all scoped slots -->
    <template
      v-for="slot in Object.keys($scopedSlots)"
      :slot="slot"
      slot-scope="scope"
    >
      <slot
        :name="slot"
        v-bind="
          // @ts-ignore
          scope
        "
      />
    </template>

    <!-- Pass on all named slots -->
    <slot v-for="slot in Object.keys($slots)" :slot="slot" :name="slot" />

    <template #footer.page-text="footerPageTextProps">
      <div class="d-flex align-center items-page-select">
        <span>{{ tc('data_table.items_no') }}</span>
        <v-select
          v-if="footerPageTextProps.itemsLength > 0"
          v-model="currentPage"
          auto
          hide-details
          :disabled="footerPageTextProps.itemsLength <= itemsPerPage"
          :items="pageSelectorData(footerPageTextProps)"
          item-value="value"
          item-text="text"
        />
        <span v-else class="mr-1">{{ footerPageTextProps.itemsLength }}</span>
        <span>
          {{ tc('common.of') }} {{ footerPageTextProps.itemsLength }}
        </span>
      </div>
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
      >
        <template #page-text="footerPageTextProps">
          <div class="d-flex align-center items-page-select">
            <span>{{ tc('data_table.items_no') }}</span>
            <v-select
              v-if="footerPageTextProps.itemsLength > 0"
              v-model="currentPage"
              auto
              hide-details
              :disabled="footerPageTextProps.itemsLength <= itemsPerPage"
              :items="pageSelectorData(footerPageTextProps)"
              item-value="value"
              item-text="text"
            />
            <span v-else class="mr-1">
              {{ footerPageTextProps.itemsLength }}
            </span>
            <span>
              {{ tc('common.of') }} {{ footerPageTextProps.itemsLength }}
            </span>
          </div>
        </template>
      </v-data-footer>
      <v-divider />
    </template>
  </v-data-table>
</template>

<script setup lang="ts">
import { type PropType, useListeners } from 'vue';
import { type DataTableHeader } from 'vuetify';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const props = defineProps({
  sortDesc: { required: false, type: Boolean, default: true },
  mustSort: { required: false, type: Boolean, default: true },
  items: { required: true, type: Array },
  headers: { required: true, type: Array as PropType<DataTableHeader[]> },
  expanded: { required: false, type: Array, default: () => [] },
  itemClass: { required: false, type: [String, Function], default: () => '' },
  hideDefaultFooter: { required: false, type: Boolean, default: false },
  container: { required: false, type: HTMLDivElement, default: () => null },
  loading: { required: false, type: Boolean, default: false },
  loadingText: { required: false, type: String, default: '' }
});

const rootAttrs = useAttrs();
const rootListeners = useListeners();
const frontendSettingsStore = useFrontendSettingsStore();
const { itemsPerPage } = storeToRefs(frontendSettingsStore);
const { container } = toRefs(props);

const tableRef = ref<any>(null);
const currentPage = ref<number>(1);
const { footerProps } = useFooterProps();

const onItemsPerPageChange = async (newValue: number) => {
  if (get(itemsPerPage) === newValue) return;

  await frontendSettingsStore.updateSetting({
    itemsPerPage: newValue
  });
};

const scrollToTop = () => {
  const { top } = useElementBounding(tableRef);
  const { top: containerTop } = useElementBounding(container);

  const tableContainer = get(container);
  const wrapper = tableContainer ?? document.body;
  const table = get(tableRef);

  if (!table || !wrapper) return;

  const tableTop = get(top);
  if (get(container)) {
    wrapper.scrollTop =
      tableTop + wrapper.scrollTop - get(containerTop) - table.$el.scrollTop;
  } else {
    wrapper.scrollTop = tableTop + wrapper.scrollTop - 64;
  }
};

const pageSelectorData = (props: {
  pageStart: number;
  pageStop: number;
  itemsLength: number;
}) => {
  const itemsLength = props.itemsLength;
  const perPage = get(itemsPerPage);
  const totalPage = Math.ceil(itemsLength / perPage);

  return new Array(totalPage).fill(0).map((item, index) => {
    return {
      value: index + 1,
      text: `${index * perPage + 1} - ${Math.min(
        (index + 1) * perPage,
        itemsLength
      )}`
    };
  });
};

const { tc } = useI18n();
</script>

<style scoped lang="scss">
/* stylelint-disable selector-class-pattern,selector-nested-pattern,no-descending-specificity */

:deep(.v-data-table) {
  .v-data-table__expanded {
    &__content {
      background-color: var(--v-rotki-light-grey-base) !important;
      box-shadow: none !important;
    }
  }

  .v-data-table--mobile {
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

.theme {
  &--dark {
    :deep(.v-data-table) {
      .v-data-table__expanded {
        &__content {
          background-color: var(--v-dark-lighten1) !important;
        }
      }
    }
  }
}

.items-page-select {
  display: flex;

  :deep(.v-input) {
    margin: 13px 0.5rem;
    font-size: 0.75rem;
    width: 100px;
    max-width: 100%;
    flex: 0 1 0;
    padding: 0;
    position: initial;

    .v-select__selections {
      .v-select__selection {
        overflow: visible;
        padding-right: 0.5rem;
      }
    }
  }
}

/* stylelint-enable selector-class-pattern,selector-nested-pattern,no-descending-specificity */
</style>
