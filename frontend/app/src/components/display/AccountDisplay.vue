<template>
  <v-row align="center" no-gutters class="flex-nowrap">
    <v-col cols="auto">
      <v-avatar left size="28px">
        <asset-icon size="24px" :identifier="account.chain" />
      </v-avatar>
    </v-col>

    <v-col class="font-weight-bold mr-1 account-display__label text-no-wrap">
      <span class="text-truncate">
        {{ account.label }}
      </span>
    </v-col>
    <v-col
      cols="auto"
      :class="privacyMode ? 'blur-content' : ''"
      class="text-no-wrap"
    >
      ({{ truncateAddress(address) }})
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { truncateAddress } from '@/filters';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { GeneralAccount } from '@/typing/types';
import { randomHex } from '@/typing/utils';

@Component({
  components: { AssetIcon },
  computed: { ...mapState('session', ['privacyMode']) }
})
export default class AccountDisplay extends Mixins(ScrambleMixin) {
  @Prop({ required: true })
  account!: GeneralAccount;
  privacyMode!: boolean;
  readonly truncateAddress = truncateAddress;

  get address(): string {
    if (!this.scrambleData) {
      return this.account.address;
    }
    return randomHex();
  }
}
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}

.account-display {
  &__label {
    > span {
      display: inline-block;
      text-overflow: clip;
      padding-top: 6px;
      line-height: 20px;
      max-width: 180px;
    }
  }
}
</style>
