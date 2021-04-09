<template>
  <span>
    <v-avatar left>
      <asset-icon size="24px" :identifier="account.chain" />
    </v-avatar>
    <span class="font-weight-bold mr-1">{{ account.label }}</span>
    <span :class="privacyMode ? 'blur-content' : ''">
      ({{ address | truncateAddress }})
    </span>
  </span>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
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
</style>
