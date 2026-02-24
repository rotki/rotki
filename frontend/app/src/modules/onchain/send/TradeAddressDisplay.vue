<script setup lang="ts">
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';

const { address, chain, name, readonly, dense } = defineProps<{
  address: string;
  chain?: string;
  name?: string;
  readonly?: boolean;
  dense?: boolean;
}>();

const { addressNameSelector } = useAddressesNamesStore();

const addressName = addressNameSelector(computed<string>(() => address), computed<string>(() => chain ?? ''));

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
