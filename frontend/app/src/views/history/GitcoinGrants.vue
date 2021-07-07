<template>
  <grants v-if="premium" />
  <no-premium-placeholder v-else :text="$t('gitcoin_grants.text')" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import Grants from '@/components/history/gitcoin-grants/Grants.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import PremiumMixin from '@/mixins/premium-mixin';

export default defineComponent({
  name: 'GitcoinGrants',
  components: { NoPremiumPlaceholder, Grants },
  mixins: [PremiumMixin]
});
</script>