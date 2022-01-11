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
    @update:items-per-page="onSelectionChange($event)"
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
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapState } from 'vuex';
import { footerProps } from '@/config/datatable.common';
import SettingsMixin from '@/mixins/settings-mixin';
import { ITEMS_PER_PAGE } from '@/types/frontend-settings';

@Component({
  computed: {
    ...mapState('settings', [ITEMS_PER_PAGE])
  }
})
export default class DataTable extends Mixins(SettingsMixin) {
  readonly footerProps = footerProps;
  itemsPerPage!: number;

  @Prop({ required: false, default: true, type: Boolean })
  sortDesc!: boolean;
  @Prop({ required: true, type: Array })
  items!: any[];
  @Prop({ required: true, type: Array })
  headers!: DataTableHeader[];
  @Prop({ required: false, type: Array, default: () => [] })
  expanded!: any[];
  @Prop({ required: false, type: [String, Function], default: () => '' })
  itemClass!: string | Function;

  async onSelectionChange(itemsPerPage: number) {
    await this.updateSetting({
      [ITEMS_PER_PAGE]: itemsPerPage
    });
  }

  scrollToTop() {
    const table = this.$refs.table as any;
    this.$vuetify.goTo(table, {
      container: document.querySelector('.app-main') as HTMLElement
    });
  }
}
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
