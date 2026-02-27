<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { usePremium } from '@/composables/premium';

withDefaults(
  defineProps<{
    hideOnSmallScreen?: boolean;
  }>(),
  {
    hideOnSmallScreen: false,
  },
);

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();
const { isLgAndDown } = useBreakpoint();
</script>

<template>
  <div class="mr-2">
    <RuiTooltip
      :popper="{ placement: 'bottom' }"
      :disabled="!(isLgAndDown && hideOnSmallScreen)"
      :open-delay="400"
    >
      <template #activator>
        <ExternalLink
          custom
          :premium="!premium"
          :url="premium ? externalLinks.manageSubscriptions : undefined"
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
            {{ premium ? t('premium_placeholder.upgrade_plan') : t('premium_settings.get') }}
          </RuiButton>
        </ExternalLink>
      </template>
      <span>{{ premium ? t('premium_placeholder.upgrade_plan') : t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
