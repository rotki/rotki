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

const { getEnsAvatarUrl } = useAddressesNamesStore();

const avatarUrl: ComputedRef<string | null> = computed(() => {
  if (get(blockchain) !== Blockchain.ETH) {
    return null;
  }

  return get(getEnsAvatarUrl(address));
});

const { getBlockie } = useBlockie();
const css = useCssModule();
</script>

<template>
  <v-lazy>
    <div :class="css.wrapper">
      <v-img :src="getBlockie(address)" />
      <v-img v-if="avatarUrl" :class="css.avatar" :src="avatarUrl" />
    </div>
  </v-lazy>
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
