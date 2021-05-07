<template>
  <v-data-table
    v-bind="$attrs"
    :sort-desc="sortDesc"
    must-sort
    :footer-props="footerProps"
    :items-per-page="itemsPerPage"
    @update:items-per-page="onSelectionChange($event)"
    v-on="$listeners"
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
  </v-data-table>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { footerProps } from '@/config/datatable.common';
import SettingsMixin from '@/mixins/settings-mixin';
import { ITEMS_PER_PAGE } from '@/store/settings/consts';

@Component({
  computed: {
    ...mapState('settings', [ITEMS_PER_PAGE])
  }
})
export default class DataTable extends Mixins(SettingsMixin) {
  @Prop({ required: false, default: true, type: Boolean })
  sortDesc!: boolean;

  readonly footerProps = footerProps;
  itemsPerPage!: number;

  async onSelectionChange(itemsPerPage: number) {
    await this.updateSetting({
      [ITEMS_PER_PAGE]: itemsPerPage
    });
  }
}
</script>

<style scoped lang="scss"></style>
