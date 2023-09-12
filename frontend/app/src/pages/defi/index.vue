<script setup lang="ts">
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
  <div class="container">
    <RouterView v-if="defiSetupDone" />
    <DefiWizard v-else class="mt-8" />
  </div>
</template>
