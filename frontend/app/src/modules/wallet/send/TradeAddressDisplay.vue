<script setup lang="ts">
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';

const { address, chain, name, readonly, dense } = defineProps<{
  address: string;
  chain?: string;
  name?: string;
  readonly?: boolean;
  dense?: boolean;
}>();

const { useAddressName } = useAddressNameResolution();

const addressName = useAddressName(() => address, () => chain ?? '');

const aliasName = computed<string | undefined>(() => {
  if (name) {
    return name;
  }
  return get(addressName);
});
</script>

<template>
  <div
    class="flex items-center gap-3"
    :class="{
      'hover:bg-rui-grey-50 dark:hover:bg-rui-grey-800 cursor-pointer': !readonly,
      'px-4 min-h-14': !dense,
    }"
  >
    <EnsAvatar
      :address="address"
      size="2rem"
      avatar
    />
    <div class="flex flex-col">
      <div
        class="font-mono text-rui-text-secondary text-sm"
        :class="{ '!text-xs': dense }"
      >
        {{ address }}
      </div>
      <div
        v-if="aliasName"
        class="font-medium text-sm"
      >
        {{ aliasName }}
      </div>
    </div>
  </div>
</template>
