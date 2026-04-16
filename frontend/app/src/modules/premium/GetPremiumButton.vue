<script setup lang="ts">
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { hideOnSmallScreen = false } = defineProps<{
  hideOnSmallScreen?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { premium } = usePremiumHelper();
const { isLgAndDown } = useBreakpoint();
</script>

<template>
  <div
    v-if="!premium"
    class="mr-2"
  >
    <RuiTooltip
      :popper="{ placement: 'bottom' }"
      :disabled="!(isLgAndDown && hideOnSmallScreen)"
      :open-delay="400"
    >
      <template #activator>
        <ExternalLink
          custom
          premium
        >
          <RuiButton
            :class="{ '[&_span]:!hidden lg:[&_span]:!block': hideOnSmallScreen }"
            :rounded="false"
            class="lg:!py-2"
            color="primary"
            data-cy="get-premium-button"
          >
            <template #prepend>
              <RuiIcon name="lu-crown" />
            </template>
            {{ t('premium_settings.get') }}
          </RuiButton>
        </ExternalLink>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
