<script lang="ts" setup>
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockie } from '@/modules/accounts/use-blockie';

defineOptions({
  inheritAttrs: false,
});

const { address, avatar = false, size = '24px' } = defineProps<{
  address: string;
  avatar?: boolean;
  size?: string | number;
}>();

const success = ref<boolean>(false);
const failed = ref<boolean>(false);

const { useEnsAvatarUrl } = useAddressNameResolution();

const avatarUrl = useEnsAvatarUrl(() => address);

const { getBlockie } = useBlockie();

const style = computed<Record<string, string | number>>(() => ({
  height: size,
  width: size,
  minWidth: size,
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
