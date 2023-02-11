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
  <v-tooltip v-if="canNavigateBack || page" open-delay="400" top>
    <template #activator="{ on, attrs }">
      <v-btn
        icon
        class="back-button__button"
        v-bind="attrs"
        v-on="on"
        @click="goBack()"
      >
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
    </template>
    <span>{{ t('back_button.tooltip') }}</span>
  </v-tooltip>
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
