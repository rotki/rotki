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
        <base-external-link href="https://rotki.com/products/">
          website.
        </base-external-link>
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
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { PremiumStatistics } from '@/utils/premium';

const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { MessageDialog, PremiumStatistics, BaseExternalLink },
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
