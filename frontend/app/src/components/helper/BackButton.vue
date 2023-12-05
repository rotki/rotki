<script setup lang="ts">
import { type ComputedRef } from 'vue';

const router = useRouter();

const route = useRoute();
const canNavigateBack: ComputedRef<boolean> = computed(() => {
  const canNavigateBack = get(route).meta?.canNavigateBack ?? false;
  return canNavigateBack && window.history.length > 1;
});

const page: ComputedRef<number | null> = computed(() => {
  const page = get(route).query?.page;
  if (page && typeof page === 'string') {
    const pageInt = parseInt(page);
    if (pageInt && pageInt > 1) {
      return pageInt;
    }
  }
  return null;
});

const goBack = () => {
  const pageVal = get(page);
  if (get(canNavigateBack)) {
    router.go(-1);
  } else if (pageVal) {
    router.push({
      query: {
        ...get(route).query,
        page: `${pageVal - 1}`
      }
    });
  }
};

const { t } = useI18n();
</script>

<template>
  <RuiTooltip
    v-if="canNavigateBack || page"
    :popper="{ placement: 'top' }"
    open-delay="400"
  >
    <template #activator>
      <RuiButton
        variant="text"
        icon
        class="back-button__button"
        @click="goBack()"
      >
        <RuiIcon name="arrow-left-line" />
      </RuiButton>
    </template>
    <span>{{ t('back_button.tooltip') }}</span>
  </RuiTooltip>
  <div v-else class="back-button__placeholder" />
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
