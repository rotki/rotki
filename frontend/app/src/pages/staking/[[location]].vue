<script setup lang="ts">
import type { StakingLocation } from '@/pages/staking/staking-pages';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import AppImage from '@/modules/shell/components/AppImage.vue';
import FullSizeContent from '@/modules/shell/components/FullSizeContent.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';
import { useStakingPage } from '@/pages/staking/use-staking-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.staking'), icon: 'lu-layers', section: 1, order: 60, drawer: 'staking' },
    noteLocation: NoteLocation.STAKING,
  },
  props: true,
});

const { location: locationProp } = defineProps<{
  location: StakingLocation | '';
}>();

const imageSize = '64px';

const { t } = useI18n({ useScope: 'global' });

const [DefineIcon, ReuseIcon] = createReusableTemplate<{ image: string }>();

const { getRedirectLink, modelLocation, page, staking } = useStakingPage(() => locationProp);
</script>

<template>
  <div class="container">
    <RuiCard class="[&>div:first-child]:flex">
      <DefineIcon #default="{ image }">
        <AppImage
          class="icon-bg"
          fit="contain"
          size="1.5rem"
          :src="image"
        />
      </DefineIcon>
      <RuiMenuSelect
        v-model="modelLocation"
        :options="staking"
        :label="t('staking_page.dropdown_label')"
        key-attr="id"
        text-attr="name"
        hide-details
        :item-height="52"
        variant="outlined"
      >
        <template #selection="{ item: { image, name } }">
          <div class="flex items-center gap-3">
            <ReuseIcon v-bind="{ image }" />
            {{ name }}
          </div>
        </template>
        <template #item.prepend="{ item: { image } }">
          <ReuseIcon v-bind="{ image }" />
        </template>
      </RuiMenuSelect>
    </RuiCard>

    <div
      v-if="page"
      class="pt-8"
      data-testid="staking-page"
    >
      <Component :is="page" />
    </div>
    <div
      v-else
      data-testid="staking-picker"
    >
      <div class="flex items-center justify-center md:justify-end mt-2 md:mr-6 text-rui-text-secondary gap-2">
        <RuiIcon
          class="shrink-0"
          name="lu-corner-left-up"
        />
        <div class="pt-3">
          {{ t('staking_page.dropdown_hint') }}
        </div>
      </div>
      <FullSizeContent class="gap-6">
        <span class="font-bold text-h5">
          {{ t('staking_page.page.title') }}
        </span>
        <div class="flex gap-4">
          <RuiTooltip
            v-for="item in staking"
            :key="item.id"
            :open-delay="400"
          >
            <template #activator>
              <InternalLink :to="getRedirectLink(item.id)">
                <AppImage
                  :size="imageSize"
                  fit="contain"
                  :src="item.image"
                />
              </InternalLink>
            </template>
            {{ item.name }}
          </RuiTooltip>
        </div>

        <div class="text-body-1 text-rui-text-secondary text-center max-w-[37rem]">
          {{ t('staking_page.page.description') }}
        </div>
      </FullSizeContent>
    </div>
  </div>
</template>
