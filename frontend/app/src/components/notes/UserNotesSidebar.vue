<script setup lang="ts">
import UserNotesList from '@/components/notes/UserNotesList.vue';
import { useNotesCount } from '@/composables/notes/use-notes-count';
import { useAppRoutes } from '@/router/routes';
import { NoteLocation } from '@/types/notes';

const display = defineModel<boolean>({ required: true });

const [DefineCountBadge, ReuseCountBadge] = createReusableTemplate<{ count: number }>();

const { t } = useI18n({ useScope: 'global' });

const tab = ref<number>(0);

const openDialog = ref<boolean>(false);

const { globalNotesCount, location, notesCount } = useNotesCount();

const { appRoutes } = useAppRoutes();

function getNoteLocationKey(key: string): string | null {
  const index = Object.values<string>(NoteLocation).indexOf(key);
  if (index > -1)
    return Object.keys(NoteLocation)[index];

  return null;
}

const locationName = computed<string>(() => {
  const locationVal = get(location);
  if (!locationVal)
    return '';

  const noteLocationKey = getNoteLocationKey(locationVal);
  if (!noteLocationKey)
    return '';

  const Routes = get(appRoutes);
  const keyIn = (key: string): key is keyof typeof Routes => key in Routes;

  if (keyIn(noteLocationKey))
    return Routes[noteLocationKey].text;

  return '';
});

watch(locationName, (locationName) => {
  if (locationName === '')
    set(tab, 0);
});
</script>

<template>
  <DefineCountBadge #default="{ count }">
    <div
      v-if="count"
      class="size-5 flex items-center justify-center rounded-full bg-rui-primary text-white text-xs"
    >
      {{ count }}
    </div>
  </DefineCountBadge>

  <RuiNavigationDrawer
    v-model="display"
    width="460px"
    temporary
    :stateless="openDialog"
    class="flex flex-col"
    position="right"
  >
    <div class="flex items-center justify-between gap-2 w-full border-b border-default">
      <RuiTabs
        v-model="tab"
        class="tabs"
        color="primary"
      >
        <RuiTab>
          <template #prepend>
            <ReuseCountBadge :count="globalNotesCount" />
          </template>
          {{ t('notes_menu.tabs.general') }}
        </RuiTab>
        <RuiTab v-if="locationName">
          <template #prepend>
            <ReuseCountBadge :count="notesCount" />
          </template>
          <RuiTooltip
            :popper="{ placement: 'bottom' }"
            :open-delay="400"
          >
            <template #activator>
              {{ t('notes_menu.tabs.in_this_page', { page: locationName }) }}
            </template>
            {{
              t('notes_menu.tabs.in_this_page_tooltip', {
                page: locationName,
              })
            }}
          </RuiTooltip>
        </RuiTab>
      </RuiTabs>

      <RuiButton
        class="!p-2"
        variant="text"
        icon
        @click="display = false"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>

    <UserNotesList
      v-if="display"
      :key="location + tab"
      v-model:open="openDialog"
      :location="tab === 0 ? NoteLocation.GLOBAL : location"
    />
  </RuiNavigationDrawer>
</template>
