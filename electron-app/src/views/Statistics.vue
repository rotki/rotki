<template>
  <v-container>
    <div id="statistics">
      <div class="row">
        <div class="col-lg-12">
          <h1 class="page-header">Statistics</h1>
        </div>
      </div>
      <div v-if="!premium">
        No premium subscription detected. Statistics are only available to
        premium users. <br />
        To get a premium subscription please visit our
        <a href="https://rotki.com/products" target="_blank">website</a>.
      </div>
      <div v-else>
        <premium-statistics
          :service="$api"
          :floating-precision="floatingPrecision"
        ></premium-statistics>
      </div>
    </div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { PremiumStatistics } from '@/utils/premium';

const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { MessageDialog, PremiumStatistics },
  computed: {
    ...mapState(['premium']),
    ...mapGetters(['floatingPrecision'])
  }
})
export default class Statistics extends Vue {
  premium!: boolean;
  floatingPrecision!: number;

  mounted() {
    if (!this.premium) {
      return;
    }
  }
}
</script>

<style scoped></style>
