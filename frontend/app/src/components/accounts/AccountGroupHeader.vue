<template>
  <div v-if="!group" class="font-weight-medium">
    {{ $t('account_group_header.standalone') }}
  </div>
  <div v-else>
    <v-btn small icon @click="expandClicked">
      <v-icon v-if="expanded" small>mdi-chevron-up</v-icon>
      <v-icon v-else small>mdi-chevron-down</v-icon>
    </v-btn>
    <span class="font-weight-medium">
      {{ $t('account_group_header.xpub') }}
    </span>
    <span :style="privacyStyle">
      <v-tooltip top open-delay="400">
        <template #activator="{ on }">
          <span v-on="on">{{ displayXpub }}</span>
        </template>
        <span> {{ xpub.xpub }} </span>
      </v-tooltip>
    </span>
    <copy-button
      :value="xpub.xpub"
      :tooltip="$t('account_group_header.copy_tooltip')"
    />
    <span v-if="xpub.derivationPath" :style="privacyStyle">
      <span class="font-weight-medium">
        {{ $t('account_group_header.derivation_path') }}
      </span>
      {{ xpub.derivationPath }}
    </span>

    <v-tooltip top open-delay="400">
      <template #activator="{ on }">
        <v-btn small icon class="ml-2" v-on="on" @click="deleteClicked(xpub)">
          <v-icon small>mdi-delete-outline</v-icon>
        </v-btn>
      </template>
      <span> {{ $t('account_group_header.delete_tooltip') }} </span>
    </v-tooltip>
  </div>
</template>
<script lang="ts">
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import CopyButton from '@/components/helper/CopyButton.vue';
import { truncateAddress, truncationPoints } from '@/filters';
import PrivacyMixin from '@/mixins/privacy-mixin';
import { XpubPayload } from '@/store/balances/types';

@Component({
  components: { CopyButton }
})
export default class AccountGroupHeader extends Mixins(PrivacyMixin) {
  @Prop({ required: true, type: String })
  group!: string;
  @Prop({ required: true, type: Object })
  xpub!: XpubPayload;
  @Prop({ required: true, type: Boolean })
  expanded!: boolean;

  get displayXpub(): string {
    return truncateAddress(
      this.xpub.xpub,
      truncationPoints[this.$vuetify.breakpoint.name] ?? 4
    );
  }

  @Emit()
  deleteClicked(_payload: XpubPayload) {}

  @Emit()
  expandClicked() {}
}
</script>
