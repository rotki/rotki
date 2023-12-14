<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    event: { counterparty: string | null; address?: string | null };
    text?: boolean;
  }>(),
  {
    text: false
  }
);

const { event } = toRefs(props);

const { getEventCounterpartyData } = useHistoryEventMappings();

const counterparty = getEventCounterpartyData(event);
const imagePath = '/assets/images/protocols/';

const [DefineImage, ReuseImage] = createReusableTemplate();
const [DefineText, ReuseText] = createReusableTemplate();
</script>

<template>
  <div>
    <DefineImage>
      <div class="rounded-full overflow-hidden bg-white">
        <div v-if="counterparty">
          <RuiIcon
            v-if="counterparty.icon"
            :name="counterparty.icon"
            :color="counterparty.color"
          />

          <AppImage
            v-else-if="counterparty.image"
            :src="`${imagePath}${counterparty.image}`"
            contain
            size="20px"
          />

          <EnsAvatar v-else size="20px" :address="counterparty.label" />
        </div>
        <EnsAvatar
          v-else-if="event.address"
          size="20px"
          :address="event.address"
          avatar
        />
      </div>
    </DefineImage>
    <DefineText>
      <div>{{ counterparty?.label || event?.address }}</div>
    </DefineText>
    <template v-if="counterparty || event.address">
      <RuiBadge
        v-if="!text"
        class="[&_span]:!px-0"
        color="default"
        offset-x="-4"
        offset-y="4"
      >
        <template #icon>
          <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
            <template #activator>
              <ReuseImage />
            </template>
            <ReuseText />
          </RuiTooltip>
        </template>
        <slot />
      </RuiBadge>
      <div v-else class="flex items-center gap-2">
        <AdaptiveWrapper>
          <ReuseImage />
        </AdaptiveWrapper>
        <ReuseText />
      </div>
    </template>
    <slot v-else />
  </div>
</template>
