<template>
  <div class="d-flex flex-row">
    <span v-if="fullAddress" :class="privacyMode ? 'blur-content' : null">
      {{ text }}
    </span>
    <v-tooltip v-else top open-delay="400">
      <template #activator="{ on, attrs }">
        <span
          :class="privacyMode ? 'blur-content' : null"
          v-bind="attrs"
          v-on="on"
        >
          {{ text | truncateAddress }}
        </span>
      </template>
      <span> {{ text }} </span>
    </v-tooltip>
    <v-tooltip top open-delay="600">
      <template #activator="{ on, attrs }">
        <v-btn
          x-small
          icon
          v-bind="attrs"
          width="20px"
          color="red"
          class="primary--text grey lighten-4 ml-2"
          v-on="on"
          @click="copyText(text)"
        >
          <v-icon x-small>
            mdi-content-copy
          </v-icon>
        </v-btn>
      </template>
      <span>{{ $t('hash_link.copy') }}</span>
    </v-tooltip>
    <v-tooltip top open-delay="600">
      <template #activator="{ on, attrs }">
        <v-btn
          v-if="!!baseUrl"
          x-small
          icon
          v-bind="attrs"
          width="20px"
          color="red"
          class="primary--text grey lighten-4 ml-1 mr-2"
          v-on="on"
          @click="openLink()"
        >
          <v-icon x-small>
            mdi-link-variant
          </v-icon>
        </v-btn>
      </template>
      <span>{{ $t('hash_link.open_link') }}</span>
    </v-tooltip>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';

@Component({
  computed: {
    ...mapState('session', ['privacyMode'])
  }
})
export default class HashLink extends Vue {
  @Prop({ required: true, type: String })
  text!: string;
  @Prop({
    required: false,
    type: String,
    default: 'https://etherscan.io/address/'
  })
  baseUrl!: string | null;
  @Prop({ required: false, type: Boolean, default: false })
  fullAddress!: boolean;

  privacyMode!: boolean;

  copyText(text: string) {
    navigator.clipboard.writeText(text);
  }

  openLink() {
    const href = this.baseUrl + this.text;
    this.$interop.openUrl(href);
  }
}
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.3em);
}
</style>
