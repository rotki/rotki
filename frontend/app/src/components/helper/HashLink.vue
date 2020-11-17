<template>
  <div class="d-flex flex-row shrink align-center">
    <span v-if="!linkOnly">
      <span v-if="fullAddress" :class="privacyMode ? 'blur-content' : null">
        {{ displayText }}
      </span>
      <v-tooltip v-else top open-delay="400">
        <template #activator="{ on, attrs }">
          <span
            :class="privacyMode ? 'blur-content' : null"
            v-bind="attrs"
            v-on="on"
          >
            {{ displayText | truncateAddress }}
          </span>
        </template>
        <span> {{ displayText }} </span>
      </v-tooltip>
    </span>
    <v-tooltip v-if="!linkOnly" top open-delay="600">
      <template #activator="{ on, attrs }">
        <v-btn
          x-small
          icon
          v-bind="attrs"
          width="20px"
          color="primary"
          class="grey lighten-4 ml-2"
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
          color="primary"
          class="grey lighten-4 ml-1"
          v-on="on"
          @click="openLink()"
        >
          <v-icon x-small>
            mdi-launch
          </v-icon>
        </v-btn>
      </template>
      <span>{{ $t('hash_link.open_link') }}</span>
    </v-tooltip>
  </div>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { randomHex } from '@/typing/utils';

@Component({
  computed: {
    ...mapState('session', ['privacyMode'])
  }
})
export default class HashLink extends Mixins(ScrambleMixin) {
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
  @Prop({ required: false, type: Boolean, default: false })
  linkOnly!: boolean;

  get displayText(): string {
    if (!this.scrambleData) {
      return this.text;
    }
    const length = this.baseUrl && this.baseUrl.includes('tx') ? 64 : 40;
    return randomHex(length);
  }

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
