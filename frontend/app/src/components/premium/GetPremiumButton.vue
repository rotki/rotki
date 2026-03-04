<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { usePremiumHelper } from '@/composables/premium';

const { hideOnSmallScreen = false } = defineProps<{
  hideOnSmallScreen?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const { currentTier, premium } = usePremiumHelper();
const { isLgAndDown } = useBreakpoint();

const tierLabel = computed<string>(() => {
  const tier = get(currentTier);
  return tier ? t('premium_placeholder.current_plan', { tier }) : t('premium_placeholder.upgrade_plan');
});
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
          v-if="!premium"
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
        <ExternalLink
          v-else
          custom
          :url="externalLinks.manageSubscriptions"
        >
          <RuiChip
            size="sm"
            variant="outlined"
            color="primary"
            data-cy="get-premium-button"
            class="!cursor-pointer"
          >
            {{ tierLabel }}
          </RuiChip>
        </ExternalLink>
      </template>
      <span>{{ premium ? tierLabel : t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
