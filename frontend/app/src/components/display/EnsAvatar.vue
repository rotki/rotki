<script lang="ts" setup>
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ComputedRef } from 'vue';

const props = withDefaults(
  defineProps<{
    address: string;
    blockchain?: Blockchain;
  }>(),
  {
    blockchain: Blockchain.ETH
  }
);

const { address, blockchain } = toRefs(props);

const { ensAvatarUrl } = useAddressesNamesStore();

const avatarUrl: ComputedRef<string | null> = computed(() => {
  if (get(blockchain) !== Blockchain.ETH) {
    return null;
  }

  return get(ensAvatarUrl(address));
});

const { getBlockie } = useBlockie();
const css = useCssModule();
</script>

<template>
  <div :class="css.wrapper">
    <v-img :src="getBlockie(address)" />
    <v-img v-if="avatarUrl" :class="css.avatar" :src="avatarUrl" />
  </div>
</template>
<style lang="scss" module>
.wrapper {
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
}

.avatar {
  position: absolute;
  z-index: 2;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}
</style>
