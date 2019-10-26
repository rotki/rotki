<template>
  <div id="settings-accounting"></div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import {
  add_accounting_settings_listeners,
  create_accounting_settings
} from '@/legacy/accounting_settings';
import { create_or_reload_page } from '@/legacy/navigation';

@Component({})
export default class Accounting extends Vue {
  mounted() {
    create_or_reload_page(
      'accounting_settings',
      create_accounting_settings,
      add_accounting_settings_listeners,
      'settings-accounting'
    );
  }
}
</script>

<style scoped></style>
