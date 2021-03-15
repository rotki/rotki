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
          <v-icon x-small> mdi-content-copy </v-icon>
        </v-btn>
      </template>
      <span>{{ $t('hash_link.copy') }}</span>
    </v-tooltip>
    <v-tooltip v-if="!noLink" top open-delay="600" max-width="400">
      <template #activator="{ on, attrs }">
        <v-btn
          v-if="!!base"
          x-small
          icon
          v-bind="attrs"
          width="20px"
          color="primary"
          class="grey lighten-4 ml-1"
          :href="href"
          :target="target"
          v-on="on"
          @click="openLink()"
        >
          <v-icon x-small> mdi-launch </v-icon>
        </v-btn>
      </template>
      <span>{{ $t('hash_link.open_link', { url }) }}</span>
    </v-tooltip>
  </div>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { explorerUrls } from '@/components/helper/asset-urls';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { ExplorersSettings } from '@/store/settings/types';
import { Blockchain, ETH } from '@/typing/types';
import { randomHex } from '@/typing/utils';

@Component({
  computed: {
    ...mapState('session', ['privacyMode']),
    ...mapState('settings', ['explorers'])
  }
})
export default class HashLink extends Mixins(ScrambleMixin) {
  @Prop({ required: true, type: String })
  text!: string;
  @Prop({ required: false, type: Boolean, default: false })
  fullAddress!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  linkOnly!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  noLink!: boolean;
  @Prop({ required: false, type: String, default: '' })
  baseUrl!: string;
  @Prop({ required: false, type: String, default: ETH })
  chain!: Blockchain | 'ETC';
  @Prop({ required: false, type: Boolean, default: false })
  tx!: Boolean;

  get displayText(): string {
    if (!this.scrambleData) {
      return this.text;
    }
    const length = this.tx ? 64 : 40;
    return randomHex(length);
  }

  privacyMode!: boolean;
  explorers!: ExplorersSettings;

  get base(): string {
    if (this.baseUrl) {
      return this.baseUrl;
    }
    const explorersSetting = this.explorers[this.chain];
    const defaultSetting = explorerUrls[this.chain];
    const baseUrl = this.tx
      ? explorersSetting?.transaction ?? defaultSetting.transaction
      : explorersSetting?.address ?? defaultSetting.address;

    return baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
  }

  copyText(text: string) {
    if (!navigator.clipboard) {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed'; //avoid scrolling to bottom
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
      } finally {
        document.body.removeChild(textArea);
      }
    } else {
      navigator.clipboard.writeText(text);
    }
  }

  get url(): string {
    return this.base + this.text;
  }

  get href(): string | undefined {
    if (this.$interop.isPackaged) {
      return undefined;
    }

    return this.url;
  }

  get target(): string | undefined {
    if (this.$interop.isPackaged) {
      return undefined;
    }
    return '_blank';
  }

  openLink() {
    this.$interop.openUrl(this.url);
  }
}
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.3em);
}
</style>
