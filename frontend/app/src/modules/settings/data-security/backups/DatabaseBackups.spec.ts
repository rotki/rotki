import type { UserDbBackupWithId } from '@/modules/session/backup';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref } from 'vue';
import DatabaseBackups from '@/modules/settings/data-security/backups/DatabaseBackups.vue';

vi.mock('@/modules/session/api/use-backup-api', () => ({
  useBackupApi: (): Record<string, unknown> => ({ fileUrl: (path: string): string => path }),
}));

vi.mock('@/modules/settings/use-setting', async () => {
  const { ref } = await import('vue');
  return { useSetting: (): Ref<string> => ref<string>('%d/%m/%Y') };
});

vi.mock('@/modules/core/table/use-remember-table-sorting', () => ({
  TableId: { USER_DB_BACKUP: 'user-db-backup' },
  useRememberTableSorting: vi.fn(),
}));

const TableStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue', 'sort', 'rows', 'cols', 'loading'],
  template: '<div><div v-for="row in rows" :key="row.id"><slot name="item.actions" :row="row" /></div><slot name="body.append" /></div>',
});

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
});

const RowAppendStub = defineComponent({
  props: ['labelColspan', 'label', 'rightPatchColspan'],
  template: '<div />',
});

function backupRow(id: number): UserDbBackupWithId {
  return { id, size: 1024, time: 1700000000 + id, version: 50 };
}

function createWrapper(selectionMode: boolean, selected: UserDbBackupWithId[] = []): VueWrapper<any> {
  return mount(DatabaseBackups, {
    global: { stubs: { RowAppend: RowAppendStub, RuiDataTable: TableStub, RuiMenu } },
    props: { directory: '/backups', items: [backupRow(1), backupRow(2)], selected, selectionMode },
  });
}

describe('modules/settings/data-security/backups/DatabaseBackups', () => {
  it('should give the table no selection, so it shows no checkboxes, outside selection mode', () => {
    const wrapper = createWrapper(false, [backupRow(1)]);

    expect(wrapper.findComponent(TableStub).props('modelValue')).toBeUndefined();
    expect(wrapper.findComponent(RowAppendStub).props('labelColspan')).toBe(2);
  });

  it('should hand the table the selected ids and widen the total label in selection mode', () => {
    const wrapper = createWrapper(true, [backupRow(2)]);

    expect(wrapper.findComponent(TableStub).props('modelValue')).toEqual([2]);
    expect(wrapper.findComponent(RowAppendStub).props('labelColspan')).toBe(3);
  });

  it('should turn ticked ids back into the backup rows', async () => {
    const wrapper = createWrapper(true);

    wrapper.findComponent(TableStub).vm.$emit('update:modelValue', [1]);
    await nextTick();

    expect(wrapper.emitted('update:selected')?.at(-1)).toEqual([[backupRow(1)]]);
  });

  it('should ask beside the delete button, naming the backup, and emit nothing until confirmed', async () => {
    const wrapper = createWrapper(false);

    await wrapper.findAll('[data-testid=backup-delete]')[1].trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').text()).toMatch(/database_backups\.confirm\.message::.+, 1024\.00/);
    expect(wrapper.emitted('remove')).toBeUndefined();
  });

  it('should emit remove with the row once its question is confirmed', async () => {
    const wrapper = createWrapper(false);

    await wrapper.findAll('[data-testid=backup-delete]')[1].trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('remove')).toEqual([[backupRow(2)]]);
  });
});
