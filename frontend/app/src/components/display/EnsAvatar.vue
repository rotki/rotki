<script lang="ts" setup>
import { Blockchain } from '@rotki/common';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    address: string;
    blockchain?: Blockchain;
    avatar?: boolean;
    size?: string | number;
  }>(),
  {
    blockchain: Blockchain.ETH,
    avatar: false,
    size: '24px',
  },
);

const success = ref<boolean>(false);
const failed = ref<boolean>(false);

const { getEnsAvatarUrl } = useAddressesNamesStore();

const avatarUrl = computed<string | null>(() => {
  if (props.blockchain !== Blockchain.ETH)
    return null;

  return get(getEnsAvatarUrl(props.address));
});

const { getBlockie } = useBlockie();

const style = computed(() => ({
  width: props.size,
  height: props.size,
}));
</script>

<template>
  <img
    v-if="!avatarUrl || failed"
    :src="getBlockie(address)"
    loading="lazy"
    :alt="address"
    :height="size"
    :width="size"
    :style="style"
    :class="{
      'rounded-full': avatar,
    }"
  />
  <div
    v-else-if="avatarUrl"
    :style="style"
    :class="{
      'skeleton': !success,
      'rounded-full': avatar,
      'rounded-xl': !avatar,
    }"
  >
    <img
      v-if="avatarUrl"
      :alt="address"
      loading="lazy"
      :class="{
        'rounded-full': avatar,
        'rounded-xl': !avatar,
      }"
      :style="style"
      :height="size"
      :width="size"
      :src="avatarUrl"
      @load="success = true"
      @error="failed = true"
    />
  </div>
</template>
