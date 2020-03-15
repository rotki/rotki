<template>
  <v-tooltip v-if="updateNeeded" bottom>
    <template #activator="{ on }">
      <v-btn text icon @click="openLink()">
        <v-icon color="error" dark v-on="on">
          fa fa-arrow-circle-o-up
        </v-icon>
      </v-btn>
    </template>
    <span>
      An Updated Version ({{ version.latestVersion }}) of Rotki is available
    </span>
  </v-tooltip>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import { Version } from '@/store/store';

@Component({
  computed: {
    ...mapState(['version']),
    ...mapGetters(['updateNeeded'])
  }
})
export default class UpdateIndicator extends Vue {
  updateNeeded!: boolean;
  version!: Version;

  openLink() {
    this.$interop.openUrl(this.version.downloadUrl);
  }
}
</script>

<style scoped></style>
