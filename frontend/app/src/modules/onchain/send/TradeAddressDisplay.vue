<script setup lang="ts">
import EnsAvatar from '@/components/display/EnsAvatar.vue';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';

const props = defineProps<{
  address: string;
  chain?: string;
  name?: string;
  readonly?: boolean;
  dense?: boolean;
}>();

const { address, chain, name } = toRefs(props);

const { addressNameSelector } = useAddressesNamesStore();

const aliasName = computed<string | null>(() => {
  const forceName = get(name);
  if (forceName) {
    return forceName;
  }
  return get(addressNameSelector(get(address), get(chain)));
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
    <div class="rounded-full overflow-hidden">
      <EnsAvatar
        :address="address"
        size="2rem"
      />
    </div>
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
