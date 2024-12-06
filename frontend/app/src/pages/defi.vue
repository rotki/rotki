<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import { useStatusStore } from '@/store/status';
import { useMakerDaoStore } from '@/store/defi/makerdao';
import { useCompoundStore } from '@/store/defi/compound';
import { useAaveStore } from '@/store/defi/aave';
import { useYearnStore } from '@/store/defi/yearn';
import { useDefiStore } from '@/store/defi';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.DEFI,
  },
  redirect: '/defi/overview',
});
const { defiSetupDone } = storeToRefs(useFrontendSettingsStore());

const defi = useDefiStore();
const yearn = useYearnStore();
const aave = useAaveStore();
const compound = useCompoundStore();
const maker = useMakerDaoStore();

const { resetDefiStatus } = useStatusStore();

onUnmounted(() => {
  defi.$reset();
  yearn.$reset();
  aave.$reset();
  compound.$reset();
  maker.$reset();
  resetDefiStatus();
});
</script>

<template>
  <RouterView v-if="defiSetupDone" />
  <DefiWizard
    v-else
    class="mt-8"
  />
</template>
