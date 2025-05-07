<script setup lang="ts">
const router = useRouter();

const route = useRoute();
const canNavigateBack = computed<boolean>(() => {
  const canNavigateBack = get(route).meta?.canNavigateBack ?? false;
  return canNavigateBack && window.history.length > 1;
});

const page = computed<number | null>(() => {
  const page = get(route).query?.page;
  if (page && typeof page === 'string') {
    const pageInt = parseInt(page);
    if (pageInt && pageInt > 1)
      return pageInt;
  }
  return null;
});

function goBack() {
  const pageVal = get(page);
  if (get(canNavigateBack)) {
    router.go(-1);
  }
  else if (pageVal) {
    router.push({
      query: {
        ...get(route).query,
        page: `${pageVal - 1}`,
      },
    });
  }
}

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    v-if="canNavigateBack || page"
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        variant="text"
        icon
        class="back-button__button"
        @click="goBack()"
      >
        <RuiIcon name="lu-arrow-left" />
      </RuiButton>
    </template>
    <span>{{ t('back_button.tooltip') }}</span>
  </RuiTooltip>
  <div
    v-else
    class="back-button__placeholder"
  />
</template>

<style scoped lang="scss">
.back-button {
  &__button,
  &__placeholder {
    margin-left: 24px;
    width: 48px;
  }
}
</style>
