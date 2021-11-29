<template>
  <v-tooltip v-if="updateNeeded" bottom>
    <template #activator="{ on }">
      <v-btn text icon @click="openLink()">
        <v-icon color="error" dark v-on="on"> mdi-arrow-up-bold-circle </v-icon>
      </v-btn>
    </template>
    <span v-text="$t('update_indicator.version', { appVersion })" />
  </v-tooltip>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import { Version } from '@/store/types';

@Component({
  computed: {
    ...mapState(['version']),
    ...mapGetters('settings', ['versionUpdateCheckFrequency']),
    ...mapGetters(['updateNeeded'])
  }
})
export default class UpdateIndicator extends Vue {
  updateNeeded!: boolean;
  version!: Version;
  versionUpdateCheckFrequency!: number;
  refreshInterval: any;

  @Watch('versionUpdateCheckFrequency')
  async setVersionUpdateCheckInterval() {
    clearInterval(this.refreshInterval);
    const period = this.versionUpdateCheckFrequency * 60 * 60 * 1000;
    if (period > 0) {
      this.refreshInterval = setInterval(async () => {
        await this.$store.dispatch('version');
      }, period);
    }
  }

  created() {
    this.setVersionUpdateCheckInterval();
  }

  get appVersion(): string {
    return this.version.latestVersion;
  }

  openLink() {
    this.$interop.openUrl(this.version.downloadUrl);
  }
}
</script>
