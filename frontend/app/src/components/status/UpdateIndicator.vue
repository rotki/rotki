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
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import { Version } from '@/store/types';

@Component({
  computed: {
    ...mapState(['version']),
    ...mapGetters(['updateNeeded'])
  }
})
export default class UpdateIndicator extends Vue {
  updateNeeded!: boolean;
  version!: Version;

  get appVersion(): string {
    return this.version.latestVersion;
  }

  openLink() {
    this.$interop.openUrl(this.version.downloadUrl);
  }
}
</script>

<style scoped></style>
