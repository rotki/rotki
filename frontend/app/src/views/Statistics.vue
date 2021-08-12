<template>
  <v-container>
    <div id="statistics">
      <div v-if="!premium">
        <p>{{ $t('statistics.no_premium') }}</p>
        <i18n path="statistics.get_premium" tag="p">
          <base-external-link text="website." :href="$interop.premiumURL" />
        </i18n>
      </div>
      <div v-else>
        <premium-statistics
          :service="$api"
          :floating-precision="floatingPrecision"
        />
      </div>
    </div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import { PremiumStatistics } from '@/premium/premium';

@Component({
  components: { PremiumStatistics, BaseExternalLink },
  computed: {
    ...mapState('session', ['premium']),
    ...mapGetters('session', ['floatingPrecision'])
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
