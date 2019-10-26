<template>
  <div id="dashboard-wrapper">
    <div class="row">
      <div class="col-lg-12">
        <h1 class="page-header">Dashboard</h1>
      </div>
    </div>
    <div class="row">
      <div id="dashboard-contents" class="col-lg-12"></div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { create_or_reload_dashboard } from '@/legacy/dashboard';

@Component({})
export default class Dashboard extends Vue {
  mounted() {
    create_or_reload_dashboard();
  }
}
</script>

<style scoped></style>
