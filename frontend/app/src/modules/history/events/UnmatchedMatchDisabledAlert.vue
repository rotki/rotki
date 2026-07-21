<script setup lang="ts">
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const {
  variant,
  premium = false,
  currentTier = null,
  matchMinimumTier = null,
} = defineProps<{
  variant: 'bridge' | 'asset-movement';
  premium?: boolean;
  currentTier?: string | null;
  matchMinimumTier?: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    type="warning"
    size="sm"
    class="whitespace-break-spaces !py-0.5 !rounded-none"
  >
    <i18n-t
      v-if="variant === 'bridge' && premium"
      scope="global"
      keypath="bridge_matching.premium.premium_tooltip"
    >
      <template #tier>
        <strong>{{ matchMinimumTier }}</strong>
      </template>
      <template #currentTier>
        <strong>{{ currentTier }}</strong>
      </template>
      <template #link>
        <ExternalLink
          premium
          color="primary"
        >
          {{ t('asset_movement_matching.premium.link') }}
        </ExternalLink>
      </template>
    </i18n-t>
    <i18n-t
      v-else-if="variant === 'bridge'"
      scope="global"
      keypath="bridge_matching.premium.free_tooltip"
    >
      <template #tier>
        <strong>{{ matchMinimumTier }}</strong>
      </template>
      <template #link>
        <ExternalLink
          premium
          color="primary"
        >
          {{ t('asset_movement_matching.premium.link') }}
        </ExternalLink>
      </template>
    </i18n-t>
    <i18n-t
      v-else-if="premium"
      scope="global"
      keypath="asset_movement_matching.premium.premium_tooltip"
    >
      <template #tier>
        <strong>{{ matchMinimumTier }}</strong>
      </template>
      <template #currentTier>
        <strong>{{ currentTier }}</strong>
      </template>
      <template #link>
        <ExternalLink
          premium
          color="primary"
        >
          {{ t('asset_movement_matching.premium.link') }}
        </ExternalLink>
      </template>
    </i18n-t>
    <i18n-t
      v-else
      scope="global"
      keypath="asset_movement_matching.premium.free_tooltip"
    >
      <template #tier>
        <strong>{{ matchMinimumTier }}</strong>
      </template>
      <template #link>
        <ExternalLink
          premium
          color="primary"
        >
          {{ t('asset_movement_matching.premium.link') }}
        </ExternalLink>
      </template>
    </i18n-t>
  </RuiAlert>
</template>
