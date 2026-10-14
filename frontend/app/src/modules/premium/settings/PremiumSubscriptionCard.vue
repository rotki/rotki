<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import PremiumPanel from '@/modules/premium/settings/PremiumPanel.vue';
import PremiumPlanLimits from '@/modules/premium/settings/PremiumPlanLimits.vue';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { editing = false } = defineProps<{
  /** Whether the key is being replaced, which swaps the plan for the key fields. */
  editing?: boolean;
}>();

const emit = defineEmits<{
  cancel: [];
  remove: [];
  replace: [];
  save: [];
}>();

defineSlots<{
  /** The key fields, shown while the key is replaced. */
  credentials: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { currentTier } = usePremiumHelper();
</script>

<template>
  <PremiumPanel :title="t('premium_settings.subscription.title')">
    <template #header-append>
      <ExternalLink
        :url="externalLinks.manageSubscriptions"
        :text="t('premium_settings.manage_or_upgrade')"
        color="primary"
        class="text-sm"
      />
    </template>

    <div class="flex items-center gap-3">
      <div class="flex size-10 shrink-0 items-center justify-center rounded-full bg-rui-primary/10 text-rui-primary">
        <RuiIcon name="lu-crown" />
      </div>
      <div class="flex flex-col min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-base font-semibold text-rui-text">{{ t('premium_settings.title') }}</span>
          <RuiChip
            size="sm"
            variant="tonal"
            color="success"
            data-testid="premium-active"
          >
            {{ t('premium_settings.status.active') }}
          </RuiChip>
        </div>
        <span class="text-sm text-rui-text-secondary">
          {{ t('premium_placeholder.current_plan', { tier: currentTier }) }}
        </span>
      </div>
    </div>

    <div class="border-t border-rui-divider" />

    <div class="grid">
      <div
        class="[grid-area:1/1] flex flex-col gap-4 transition-[opacity,translate,visibility] duration-200 ease-out motion-reduce:transition-none"
        :class="editing ? 'invisible opacity-0 -translate-y-1' : 'visible opacity-100 translate-y-0'"
        :inert="editing"
      >
        <PremiumPlanLimits />
        <div class="border-t border-rui-divider" />
        <div class="flex items-center gap-2 text-sm text-rui-text-secondary">
          <RuiIcon
            name="lu-key-round"
            size="16"
          />
          {{ t('premium_settings.subscription.credentials_saved') }}
        </div>
      </div>
      <div
        class="[grid-area:1/1] flex flex-col gap-4 transition-[opacity,translate,visibility] duration-200 ease-out motion-reduce:transition-none"
        :class="editing ? 'visible opacity-100 translate-y-0' : 'invisible opacity-0 translate-y-1'"
        :inert="!editing"
        data-testid="premium-replace-fields"
      >
        <p class="m-0 text-sm text-rui-text-secondary">
          {{ t('premium_settings.subscription.replace_hint') }}
        </p>
        <slot name="credentials" />
      </div>
    </div>

    <template #actions>
      <template v-if="editing">
        <RuiButton
          variant="outlined"
          color="primary"
          @click="emit('cancel')"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          data-testid="premium-setup"
          @click="emit('save')"
        >
          {{ t('common.actions.save') }}
        </RuiButton>
      </template>
      <template v-else>
        <RuiButton
          variant="text"
          color="error"
          data-testid="premium-delete"
          @click="emit('remove')"
        >
          {{ t('premium_settings.actions.delete') }}
        </RuiButton>
        <RuiButton
          color="primary"
          data-testid="premium-setup"
          @click="emit('replace')"
        >
          {{ t('premium_settings.actions.replace') }}
        </RuiButton>
      </template>
    </template>
  </PremiumPanel>
</template>
