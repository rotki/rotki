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

const success: Ref<boolean> = ref(false);
const failed: Ref<boolean> = ref(false);
</script>

<template>
  <VLazy :class="css.wrapper">
    <div>
      <VImg
        v-if="!avatarUrl || failed"
        :src="getBlockie(address)"
        :class="css.avatar"
      />
      <VSkeletonLoader
        v-else-if="avatarUrl && !success"
        type="image"
        width="24px"
        height="24px"
      />
      <VImg
        v-if="avatarUrl"
        :class="css.avatar"
        :src="avatarUrl"
        @load="success = true"
        @error="failed = true"
      />
    </div>
  </VLazy>
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
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}
</style>
