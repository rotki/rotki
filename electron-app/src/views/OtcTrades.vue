<template>
  <div id="otc-trades"></div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import {
  add_otctrades_listeners,
  create_otctrades_ui
} from '@/legacy/otctrades';
import { create_or_reload_page } from '@/legacy/navigation';

@Component({})
export default class OtcTrades extends Vue {
  mounted() {
    create_or_reload_page(
      'otctrades',
      create_otctrades_ui,
      add_otctrades_listeners,
      'otc-trades'
    );
  }
}
</script>

<style scoped></style>
