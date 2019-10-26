<template>
  <div id="statistics">
    <div class="row">
      <div class="col-lg-12">
        <h1 class="page-header">Statistics</h1>
      </div>
    </div>
    <div v-if="premium">
      <div>
        <p>
          No premium subscription detected. Statistics are only available to
          premium users.
        </p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { settings } from '@/legacy/settings';
import { showError } from '@/legacy/utils';

@Component({})
export default class Statistics extends Vue {
  premium: boolean = false;
  mounted() {
    this.premium = settings.has_premium;

    if (!this.premium) {
      return;
    }

    this.$rpc
      .query_statistics_renderer()
      .then(result => {
        eval(result);
      })
      .catch(reason => {
        showError('Error at querying statistics renderer', reason.message);
      });
  }
}
</script>

<style scoped></style>
