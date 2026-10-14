<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { type MessageKey, msg } from '@/message-key';
import PremiumPanel from '@/modules/premium/settings/PremiumPanel.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

interface Feature {
  icon: string;
  title: MessageKey;
  description: MessageKey;
}

const emit = defineEmits<{
  activate: [];
}>();

defineSlots<{
  /** The key fields an existing subscriber fills in. */
  credentials: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

/** What a subscription adds, in the order a new user is most likely to care about. */
const FEATURES: Feature[] = [
  { description: msg.$t('premium_settings.upsell.features.graphs.description'), icon: 'lu-chart-line', title: msg.$t('premium_settings.upsell.features.graphs.title') },
  { description: msg.$t('premium_settings.upsell.features.mcp.description'), icon: 'lu-bot-message-square', title: msg.$t('premium_settings.upsell.features.mcp.title') },
  { description: msg.$t('premium_settings.upsell.features.sync.description'), icon: 'lu-cloud-upload', title: msg.$t('premium_settings.upsell.features.sync.title') },
  { description: msg.$t('premium_settings.upsell.features.staking.description'), icon: 'lu-layers', title: msg.$t('premium_settings.upsell.features.staking.title') },
  { description: msg.$t('premium_settings.upsell.features.limits.description'), icon: 'lu-file-chart-column', title: msg.$t('premium_settings.upsell.features.limits.title') },
  { description: msg.$t('premium_settings.upsell.features.matching.description'), icon: 'lu-git-compare-arrows', title: msg.$t('premium_settings.upsell.features.matching.title') },
];
</script>

<template>
  <PremiumPanel>
    <div class="relative overflow-hidden rounded-rui-control bg-linear-to-br from-rui-primary/15 via-rui-primary/5 to-transparent p-6 sm:p-8">
      <RuiIcon
        name="lu-crown"
        size="160"
        class="pointer-events-none absolute -right-6 -top-6 text-rui-primary/10 hidden sm:block"
      />
      <div class="relative flex flex-col gap-4 max-w-2xl">
        <div>
          <RuiChip
            size="sm"
            variant="tonal"
            color="primary"
          >
            <span class="inline-flex items-center gap-1.5">
              <RuiIcon
                name="lu-crown"
                size="14"
              />
              {{ t('premium_settings.title') }}
            </span>
          </RuiChip>
        </div>
        <div class="flex flex-col gap-2">
          <h2 class="m-0 text-2xl font-semibold text-rui-text">
            {{ t('premium_settings.upsell.title') }}
          </h2>
          <p class="m-0 text-base text-rui-text-secondary">
            {{ t('premium_settings.upsell.description') }}
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
          <ExternalLink
            :url="externalLinks.premium"
            custom
          >
            <RuiButton
              color="primary"
              size="lg"
              data-testid="premium-see-plans"
            >
              <template #append>
                <RuiIcon
                  name="lu-arrow-right"
                  size="18"
                />
              </template>
              {{ t('premium_settings.upsell.see_plans') }}
            </RuiButton>
          </ExternalLink>
          <span class="inline-flex items-center gap-1.5 text-sm text-rui-text-secondary">
            <RuiIcon
              name="lu-heart"
              size="14"
              class="text-rui-primary"
            />
            {{ t('premium_settings.upsell.supports') }}
          </span>
        </div>
      </div>
    </div>

    <ul
      class="m-0 p-0 list-none grid sm:grid-cols-2 lg:grid-cols-3 gap-3"
      data-testid="premium-upsell-features"
    >
      <li
        v-for="feature in FEATURES"
        :key="feature.title"
        class="flex gap-3 rounded-rui-control border border-rui-divider p-4 transition-colors hover:border-rui-primary/40 motion-reduce:transition-none"
      >
        <div class="flex size-9 shrink-0 items-center justify-center rounded-full bg-rui-primary/10 text-rui-primary">
          <RuiIcon
            :name="feature.icon"
            size="18"
          />
        </div>
        <div class="flex flex-col gap-0.5 min-w-0">
          <span class="text-sm font-semibold text-rui-text">{{ t(feature.title) }}</span>
          <span class="text-sm text-rui-text-secondary">{{ t(feature.description) }}</span>
        </div>
      </li>
    </ul>

    <div class="border-t border-rui-divider" />

    <div class="flex flex-col gap-1">
      <h3 class="m-0 text-base font-semibold text-rui-text">
        {{ t('premium_settings.upsell.subscribed_title') }}
      </h3>
      <p class="m-0 text-sm text-rui-text-secondary">
        {{ t('premium_settings.upsell.subscribed_description') }}
      </p>
    </div>
    <slot name="credentials" />

    <template #actions>
      <RuiButton
        color="primary"
        variant="outlined"
        data-testid="premium-setup"
        @click="emit('activate')"
      >
        {{ t('premium_settings.upsell.activate') }}
      </RuiButton>
    </template>
  </PremiumPanel>
</template>
