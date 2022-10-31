<template>
  <v-tooltip v-if="canNavigateBack" open-delay="400" top>
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
<script setup lang="ts">
import { useRouter } from '@/composables/router';

defineProps({
  canNavigateBack: { required: true, type: Boolean, default: false }
});

const router = useRouter();
const goBack = () => {
  router.go(-1);
};

const { t } = useI18n();
</script>
<style scoped lang="scss">
.back-button {
  &__button,
  &__placeholder {
    margin-left: 24px;
    width: 48px;
  }
}
</style>
