<template>
  <v-container>
    <div id="tax-report"></div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { create_or_reload_page } from '@/legacy/navigation';
import {
  add_taxreport_listeners,
  create_taxreport_ui
} from '@/legacy/taxreport';

@Component({})
export default class TaxReport extends Vue {
  mounted() {
    create_or_reload_page(
      'taxreport',
      create_taxreport_ui,
      add_taxreport_listeners,
      'tax-report'
    );
  }
}
</script>

<style scoped></style>
