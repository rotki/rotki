<template>
  <span>
    <v-avatar left>
      <crypto-icon size="24px" :symbol="account.chain" />
    </v-avatar>
    <span class="font-weight-bold mr-1">{{ account.label }}</span>
    <span :class="privacyMode ? 'blur-content' : ''">
      ({{ account.address | truncateAddress }})
    </span>
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import { GeneralAccount } from '@/typing/types';

@Component({
  components: { CryptoIcon },
  computed: { ...mapState('session', ['privacyMode']) }
})
export default class AccountDisplay extends Vue {
  @Prop({ required: true })
  account!: GeneralAccount;
  privacyMode!: boolean;
}
</script>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
