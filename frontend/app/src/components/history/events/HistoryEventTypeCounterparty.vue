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
      <div>
        <VAvatar v-if="counterparty" size="24">
          <RuiIcon
            v-if="counterparty.icon"
            :name="counterparty.icon"
            :color="counterparty.color"
          />

          <VImg
            v-else-if="counterparty.image"
            :src="`${imagePath}${counterparty.image}`"
            contain
            max-width="24px"
          />

          <EnsAvatar v-else :address="counterparty.label" />
        </VAvatar>
        <EnsAvatar v-else-if="event.address" :address="event.address" avatar />
      </div>
    </DefineImage>
    <DefineText>
      <div>{{ counterparty?.label || event?.address }}</div>
    </DefineText>
    <template v-if="counterparty || event.address">
      <VBadge v-if="!text" avatar overlap color="white">
        <template #badge>
          <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
            <template #activator>
              <ReuseImage />
            </template>
            <ReuseText />
          </RuiTooltip>
        </template>
        <slot />
      </VBadge>
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
