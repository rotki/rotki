<script setup lang="ts">
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';

defineProps<{ text: string }>();

defineSlots<{
  logo: () => any;
}>();

const { t } = useI18n();
const { isMdAndUp } = useBreakpoint();
</script>

<template>
  <FullSizeContent class="gap-4">
    <div class="flex items-center justify-center">
      <div
        class="bg-rui-grey-200 dark:bg-rui-grey-900 rounded-full mb-8"
        :class="[isMdAndUp ? 'w-64 h-64 p-16' : 'w-32 h-32 p-8']"
      >
        <slot name="logo">
          <RotkiLogo
            :size="isMdAndUp ? 8 : 4"
            logo="emptyScreen"
            unique-key="2"
          />
        </slot>
      </div>
    </div>
    <div class="text-h5">
      {{ t('no_premium_placeholder.no_premium') }}
    </div>
    <div class="text-subtitle-2 text-rui-text-secondary">
      {{ t('no_premium_placeholder.premium_only', { text }) }}
    </div>
    <i18n-t
      tag="div"
      keypath="no_premium_placeholder.get_premium"
      class="text-rui-text-secondary"
    >
      <ExternalLink
        :text="t('common.website')"
        color="primary"
        premium
      />
    </i18n-t>
  </FullSizeContent>
</template>
