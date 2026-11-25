<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { hideOnSmallScreen = false, url } = defineProps<{
  hideOnSmallScreen?: boolean;
  url?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const { premium } = usePremiumHelper();
const { isLgAndDown } = useBreakpoint();
</script>

<template>
  <div
    v-if="!premium || url"
    class="mr-2"
  >
    <RuiTooltip
      :options="{ placement: 'bottom' }"
      :disabled="!(isLgAndDown && hideOnSmallScreen)"
      :open-delay="400"
    >
      <template #activator>
        <ExternalLink
          custom
          premium
          :url="url"
        >
          <RuiButton
            :class="{ '[&_span]:hidden! lg:[&_span]:block!': hideOnSmallScreen }"
            :rounded="false"
            class="lg:py-2!"
            color="primary"
            data-testid="get-premium-button"
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
