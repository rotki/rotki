<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { useBlockie } from '@/composables/accounts/blockie';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';

const props = defineProps<{
  address: string;
  chain: string;
}>();

const { address, chain } = toRefs(props);

const { getBlockie } = useBlockie();
const { addressNameSelector } = useAddressesNamesStore();

const aliasName = computed<string | null>(() => get(addressNameSelector(get(address), get(chain))));
</script>

<template>
  <div class="flex items-center gap-4 px-4 min-h-14 hover:bg-rui-grey-50 dark:hover:bg-rui-grey-800 cursor-pointer">
    <div class="rounded-full overflow-hidden">
      <AppImage
        :src="getBlockie(address)"
        size="2rem"
      />
    </div>
    <div class="flex flex-col">
      <div class="font-mono text-rui-text-secondary text-sm">
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
