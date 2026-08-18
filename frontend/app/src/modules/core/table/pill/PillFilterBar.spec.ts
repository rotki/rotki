import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import EnumValueEditor from '@/modules/core/table/pill/EnumValueEditor.vue';
import FilterPill from '@/modules/core/table/pill/FilterPill.vue';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import PillMenu from '@/modules/core/table/pill/PillMenu.vue';
import PillNarrowList from '@/modules/core/table/pill/PillNarrowList.vue';
import PillValueEditor from '@/modules/core/table/pill/PillValueEditor.vue';
import RangeValueEditor from '@/modules/core/table/pill/RangeValueEditor.vue';

// Remembering a value writes a frontend setting; the write itself is the observable act.
interface RecentEntry { count: number; value: string }

interface FrontendPatch { recentFilterValues: Record<string, RecentEntry[]> }

const updateFrontendSetting = vi.fn(async (_settings: FrontendPatch) => ({ success: true }));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: typeof updateFrontendSetting } => ({ updateFrontendSetting }),
}));

// RuiMenu lazily teleports its content; stub it to render both slots inline so the
// activator (pill/button) and the content (editor/menu) are always in the tree.
const RuiMenuStub = defineComponent({
  name: 'RuiMenu',
  props: { disabled: { default: false, type: Boolean }, modelValue: { default: false, type: Boolean } },
  emits: ['update:modelValue'],
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

const protocol: FieldDef = {
  allowExclusion: true,
  binding: { kind: 'filter' },
  key: 'protocols',
  label: 'Protocol',
  multiple: true,
  operators: ['is', 'is_not'],
  suggest: (): string[] => ['aave', 'uniswap'],
  valueType: 'enum',
};

const account: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'param', paramKey: 'locationLabels', to: 'both' },
  key: 'account',
  label: 'Account',
  multiple: true,
  operators: ['is'],
  suggest: (): string[] => ['0xaaa', '0xbbb'],
  valueType: 'enum',
};

// Two fields that write the same wire keys, as history's action and event type do: only one of
// them may be active at a time.
const action: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'param', paramKey: 'action', to: 'url' },
  excludes: ['protocols'],
  key: 'action',
  label: 'Action',
  multiple: false,
  operators: ['is'],
  suggest: (): string[] => ['pay_fee'],
  valueType: 'enum',
};

// A collapsed range: its two bounds live under their own wire keys, which is the form a saved
// view stores and the one place a stored filter can come back as something else.
const amount: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  bounds: { lower: 'minAmount', upper: 'maxAmount' },
  key: 'amount',
  label: 'Amount',
  multiple: false,
  operators: ['between', 'gt', 'lt'],
  valueType: 'range',
};

const fields = [protocol, account];

// What a range field carries in the real adapter: it reads a typed amount into whole filters.
const typedAmount: FieldDef = {
  ...amount,
  // Set alongside `parseTyped`, the way the adapter builds a real range field: it is what gates
  // the footer's syntax examples, so a fixture with only the parser advertises nothing to type.
  matchesTyped: (query: string): boolean => /^[\d<>]/.test(query),
  parseTyped: (query: string) => (/^>\d+$/.test(query)
    ? [{ op: 'gt' as const, range: { min: query.slice(1) }, values: [] }]
    : []),
};

const labels = {
  add: 'Add filter',
  clear: 'Clear all',
  empty: 'No filters match',
  narrow: 'Filter…',
  narrowEmpty: 'No matches',
  remove: 'Remove filter',
  search: 'Filter by…',
  syntax: 'Type directly:',
};

function createWrapper(
  matches: Partial<MatchedKeyword<string>> = {},
  params: Record<string, string | string[] | boolean> = {},
  slots: Record<string, string> = {},
  fieldSet: FieldDef[] = fields,
  // Focus only lands anywhere in jsdom when the tree is actually in the document.
  options: { attachTo?: HTMLElement } = {},
): VueWrapper<InstanceType<typeof PillFilterBar>> {
  return mount(PillFilterBar, {
    ...options,
    global: {
      // The bar remembers committed free-text values through the settings repo.
      plugins: [createCustomPinia()],
      stubs: { AssetValueEditor: true, RuiAutoComplete: true, RuiMenu: RuiMenuStub },
    },
    props: { fields: fieldSet, labels, matches, params },
    slots,
  });
}

function lastEmit(wrapper: VueWrapper, event: string): unknown {
  const calls = wrapper.emitted(event);
  return calls?.at(-1)?.[0];
}

describe('pillFilterBar', () => {
  // A modifier constrains how the active filters apply, so with nothing filtered it is a control
  // that does nothing. The bar stays generic: it only knows such controls may exist.
  it('should not render the modifiers slot while nothing is filtered', () => {
    const wrapper = createWrapper({}, {}, { modifiers: '<div data-testid="modifier" />' });
    expect(wrapper.find('[data-testid=modifier]').exists()).toBe(false);
  });

  it('should render the modifiers slot once a filter is active', () => {
    const wrapper = createWrapper({ protocols: ['aave'] }, {}, { modifiers: '<div data-testid="modifier" />' });
    expect(wrapper.find('[data-testid=modifier]').exists()).toBe(true);
  });

  // Saved views are the opposite case: what a view is for is filling an empty bar, so unlike a
  // modifier it has to be there when nothing is filtered.
  it('should always render the views slot', () => {
    const empty = createWrapper({}, {}, { views: '<div data-testid="views" />' });
    expect(empty.find('[data-testid=views]').exists()).toBe(true);

    const filtered = createWrapper({ protocols: ['aave'] }, {}, { views: '<div data-testid="views" />' });
    expect(filtered.find('[data-testid=views]').exists()).toBe(true);
  });

  // Both write the same request keys, so offering the other one after the first is applied would
  // let two pills fight over them.
  it('should not offer a field excluded by an active filter', async () => {
    const wrapper = createWrapper({}, { action: 'pay_fee' }, {}, [protocol, account, action]);
    await nextTick();
    await wrapper.get('[data-testid=pill-add]').trigger('click');
    expect(wrapper.find('[data-testid=pill-menu-field][data-field=protocols]').exists()).toBe(false);
  });

  it('should offer it again once that filter is gone', async () => {
    const wrapper = createWrapper({}, {}, {}, [protocol, account, action]);
    await nextTick();
    await wrapper.get('[data-testid=pill-add]').trigger('click');
    expect(wrapper.find('[data-testid=pill-menu-field][data-field=protocols]').exists()).toBe(true);
  });

  it('should render a pill per active filter seeded from matches/params', () => {
    const wrapper = createWrapper({ protocols: ['aave'] }, { locationLabels: ['0xaaa'] });
    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(2);
  });

  it('should offer only the not-yet-active fields in the add menu', () => {
    const wrapper = createWrapper({ protocols: ['aave'] });
    expect(wrapper.findComponent(PillMenu).props('fields')).toStrictEqual([account]);
  });

  it('should emit matches without the field when a pill is removed', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] });
    wrapper.findComponent(FilterPill).vm.$emit('remove');
    await nextTick();
    expect(lastEmit(wrapper, 'update:matches')).toStrictEqual({});
  });

  it('should add a filter when a field is picked from the menu', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] });
    wrapper.findComponent(PillMenu).vm.$emit('select', account);
    await nextTick();
    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(2);
  });

  it('should open the value editor for a field added from the menu', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] });
    wrapper.findComponent(PillMenu).vm.$emit('select', account);
    await nextTick();
    await nextTick(); // addField opens the editor on the next tick, once the pill exists
    // exactly one pill menu (the newly added account field) is open
    const open = wrapper.findAllComponents(RuiMenuStub).filter(menu => menu.props('modelValue') === true);
    expect(open).toHaveLength(1);
  });

  it('should emit updated matches when the editor changes a matcher field', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] });
    wrapper.findComponent(EnumValueEditor).vm.$emit('update', { fieldKey: 'protocols', op: 'is', values: ['aave', 'curve'] });
    await nextTick();
    expect(lastEmit(wrapper, 'update:matches')).toStrictEqual({ protocols: ['aave', 'curve'] });
  });

  it('should route a param-bound field to params, not matches', async () => {
    const wrapper = createWrapper({}, { locationLabels: ['0xaaa'] });
    wrapper.findComponent(EnumValueEditor).vm.$emit('update', { fieldKey: 'account', op: 'is', values: ['0xaaa', '0xbbb'] });
    await nextTick();
    expect(lastEmit(wrapper, 'update:params')).toStrictEqual({ locationLabels: ['0xaaa', '0xbbb'] });
  });

  // What a saved view stores is whatever the bar emitted, so the claim under test is that handing
  // that back rebuilds the same pills. A range is the case worth pinning: it is the only field
  // whose value is split across two wire keys, so a view is where it would quietly come back as
  // half a filter or as the wrong operator.
  describe('applying a stored filter set', () => {
    it('should rebuild a range pill from the matches it emitted', async () => {
      const saved = createWrapper({ minAmount: '5', maxAmount: '50' }, {}, {}, [protocol, amount]);
      saved.findComponent(RangeValueEditor).vm.$emit('update', {
        fieldKey: 'amount',
        op: 'gt',
        range: { min: '10' },
        values: [],
      });
      await nextTick();

      // A `gt` filter drops the upper bound, and the operator is read back from the bound that
      // survived: storing both would put "greater than 5 - 50" on the restored pill.
      const stored = { minAmount: '10' };
      expect(lastEmit(saved, 'update:matches')).toStrictEqual(stored);

      const restored = createWrapper(stored, {}, {}, [protocol, amount]);
      const pill = restored.findComponent(FilterPill);
      expect(pill.props('filter')).toMatchObject({ fieldKey: 'amount', op: 'gt', range: { min: '10' } });
    });

    it('should replace the active filters rather than merge into them', async () => {
      const wrapper = createWrapper({ protocols: ['aave'] }, { locationLabels: ['0xaaa'] });
      expect(wrapper.findAllComponents(FilterPill)).toHaveLength(2);

      // Applying a view writes both models at once, which is what the history table does with it.
      await wrapper.setProps({ matches: { protocols: ['curve'] }, params: {} });

      const pills = wrapper.findAllComponents(FilterPill);
      expect(pills).toHaveLength(1);
      expect(pills[0].props('filter')).toMatchObject({ fieldKey: 'protocols', values: ['curve'] });
    });
  });

  describe('inline narrowing input', () => {
    async function type(wrapper: VueWrapper, value: string): Promise<void> {
      await wrapper.get('[data-testid=pill-narrow-input]').setValue(value);
    }

    it('should offer every available field before anything is typed', () => {
      const wrapper = createWrapper();

      expect(wrapper.findComponent(PillNarrowList).props('suggestions')).toStrictEqual([
        { field: protocol, kind: 'field', label: 'Protocol' },
        { field: account, kind: 'field', label: 'Account' },
      ]);
    });

    it('should narrow across fields and values at once', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'a');

      expect(wrapper.findComponent(PillNarrowList).props('suggestions')).toStrictEqual([
        { field: account, kind: 'field', label: 'Account' },
        { field: protocol, kind: 'value', label: 'aave', value: 'aave' },
        { field: protocol, kind: 'value', label: 'uniswap', value: 'uniswap' },
        { field: account, kind: 'value', label: '0xaaa', value: '0xaaa' },
      ]);
    });

    it('should not suggest a field that already has a filter', async () => {
      const wrapper = createWrapper({ protocols: ['aave'] });
      await type(wrapper, 'a');

      const suggested = wrapper.findComponent(PillNarrowList).props('suggestions');
      expect(suggested).toStrictEqual([
        { field: account, kind: 'field', label: 'Account' },
        { field: account, kind: 'value', label: '0xaaa', value: '0xaaa' },
      ]);
    });

    it('should apply a value suggestion in one step', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'aave');
      wrapper.findComponent(PillNarrowList).vm.$emit('select', { field: protocol, kind: 'value', label: 'aave', value: 'aave' });
      await nextTick();

      expect(lastEmit(wrapper, 'update:matches')).toStrictEqual({ protocols: ['aave'] });
    });

    it('should reset the query once a suggestion is applied', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'aave');
      wrapper.findComponent(PillNarrowList).vm.$emit('select', { field: protocol, kind: 'value', label: 'aave', value: 'aave' });
      await nextTick();

      expect(wrapper.get<HTMLInputElement>('[data-testid=pill-narrow-input]').element.value).toBe('');
    });

    it('should add an empty pill for a field suggestion', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'acc');
      wrapper.findComponent(PillNarrowList).vm.$emit('select', { field: account, kind: 'field', label: 'Account' });
      await nextTick();

      expect(wrapper.findAllComponents(FilterPill)).toHaveLength(1);
    });

    it('should close the popover when a field suggestion opens its editor', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'acc');
      wrapper.findComponent(PillNarrowList).vm.$emit('select', { field: account, kind: 'field', label: 'Account' });
      await nextTick();
      await nextTick(); // the editor opens a tick later, once the pill exists

      // Menus render as [pill editor, narrowing popover, add menu]: only the editor may be open,
      // never the popover that was picked from.
      const open = wrapper.findAllComponents(RuiMenuStub).map(menu => menu.props('modelValue'));
      expect(open).toStrictEqual([true, false, false]);
    });

    it('should keep the popover open when a value suggestion applies directly', async () => {
      const wrapper = createWrapper();
      await type(wrapper, 'aave');
      wrapper.findComponent(PillNarrowList).vm.$emit('select', { field: protocol, kind: 'value', label: 'aave', value: 'aave' });
      await nextTick();

      const open = wrapper.findAllComponents(RuiMenuStub).filter(menu => menu.props('modelValue') === true);
      expect(open).toHaveLength(1);
    });

    it('should apply the highlighted suggestion on enter', async () => {
      const wrapper = createWrapper();
      const input = wrapper.get('[data-testid=pill-narrow-input]');
      await input.setValue('a');
      await input.trigger('keydown', { key: 'ArrowDown' });
      await input.trigger('keydown', { key: 'Enter' });
      await nextTick();

      // ArrowDown moves off the Account field onto the first protocol value.
      expect(lastEmit(wrapper, 'update:matches')).toStrictEqual({ protocols: ['aave'] });
    });

    it('should remove the last pill on backspace in an empty input', async () => {
      const wrapper = createWrapper({ protocols: ['aave'] }, { locationLabels: ['0xaaa'] });
      await wrapper.get('[data-testid=pill-narrow-input]').trigger('keydown', { key: 'Backspace' });
      await nextTick();

      expect(lastEmit(wrapper, 'update:params')).toStrictEqual({});
      expect(wrapper.findAllComponents(FilterPill)).toHaveLength(1);
    });

    it('should keep the pills when backspace is pressed with a query typed', async () => {
      const wrapper = createWrapper({ protocols: ['aave'] });
      const input = wrapper.get('[data-testid=pill-narrow-input]');
      await input.setValue('a');
      await input.trigger('keydown', { key: 'Backspace' });
      await nextTick();

      expect(wrapper.findAllComponents(FilterPill)).toHaveLength(1);
    });

    it('should reset the query on escape', async () => {
      const wrapper = createWrapper();
      const input = wrapper.get('[data-testid=pill-narrow-input]');
      await input.setValue('a');
      await input.trigger('keydown', { key: 'Escape' });

      expect(wrapper.get<HTMLInputElement>('[data-testid=pill-narrow-input]').element.value).toBe('');
      // Back to the blank-query list, not an empty state.
      expect(wrapper.findComponent(PillNarrowList).props('suggestions')).toHaveLength(2);
    });
  });

  it('should clear every filter', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] }, { locationLabels: ['0xaaa'] });
    await wrapper.get('[data-testid=pill-clear]').trigger('click');
    expect(lastEmit(wrapper, 'update:matches')).toStrictEqual({});
    expect(lastEmit(wrapper, 'update:params')).toStrictEqual({});
  });

  // A written amount or date is offered as a whole filter rather than as a value, so applying it
  // goes through the draft the field produced instead of building one from a value string.
  it('should apply a filter read out of the typed query', async () => {
    const wrapper = createWrapper({}, {}, {}, [protocol, typedAmount]);
    await wrapper.get('[data-testid=pill-narrow-input]').setValue('>100');

    const list = wrapper.findComponent(PillNarrowList);
    const [suggestion] = list.props('suggestions');
    expect(suggestion).toMatchObject({ kind: 'filter', label: 'table_filter.operators.greater_than 100' });

    list.vm.$emit('select', suggestion);
    await nextTick();

    expect(lastEmit(wrapper, 'update:matches')).toStrictEqual({ minAmount: '100' });
  });

  // The footer teaches by demonstration: its example goes into the input, and the row it produces
  // shows up above it. Applying it outright would add a pill for an amount nobody asked for.
  it('should put a clicked syntax example in the input without filtering', async () => {
    const wrapper = createWrapper({}, {}, {}, [protocol, typedAmount]);

    wrapper.findComponent(PillNarrowList).vm.$emit('example', '>100');
    await nextTick();

    expect(wrapper.get<HTMLInputElement>('[data-testid=pill-narrow-input]').element.value).toBe('>100');
    expect(wrapper.emitted('update:matches')).toBeUndefined();
  });

  // The chip is a `button`, but nothing in the popover is ever focused and it is teleported out of
  // the input's tab order, so Tab never arrives and the mouse was the only way in. The highlight
  // therefore runs on past the last row into the footer, and Enter there does what a click does.
  it('should reach a syntax example by arrowing past the last row', async () => {
    const wrapper = createWrapper({}, {}, {}, [protocol, typedAmount]);
    const input = wrapper.get('[data-testid=pill-narrow-input]');
    await input.setValue('>100');

    const list = wrapper.findComponent(PillNarrowList);
    const rows = list.props('suggestions').length;
    const examples = list.props('examples') ?? [];
    assert(examples.length > 0, 'the footer must offer an example to arrow onto');

    // Down off the end of the rows lands on the first chip and names it to the screen reader.
    for (let step = 0; step < rows; step++)
      await input.trigger('keydown', { key: 'ArrowDown' });

    expect(list.props('highlighted')).toBe(rows);
    expect(input.attributes('aria-activedescendant')).toBe('pill-narrow-example-0');

    await input.trigger('keydown', { key: 'Enter' });

    expect(wrapper.get<HTMLInputElement>('[data-testid=pill-narrow-input]').element.value).toBe(examples[0]);
    expect(wrapper.emitted('update:matches')).toBeUndefined();
  });

  // Wrapping is what makes the footer escapable without a mouse: one Up from the top row is the
  // last chip, and one Down from it is the first row again.
  it('should wrap between the rows and the footer', async () => {
    const wrapper = createWrapper({}, {}, {}, [protocol, typedAmount]);
    const input = wrapper.get('[data-testid=pill-narrow-input]');
    await input.setValue('>100');

    const list = wrapper.findComponent(PillNarrowList);
    const total = list.props('suggestions').length + (list.props('examples') ?? []).length;

    await input.trigger('keydown', { key: 'ArrowUp' });
    expect(list.props('highlighted')).toBe(total - 1);

    await input.trigger('keydown', { key: 'ArrowDown' });
    expect(list.props('highlighted')).toBe(0);
  });

  // The example is only a starting point, so the rows it produces have to be there to pick from.
  it('should offer the filter a clicked example reads as', async () => {
    const wrapper = createWrapper({}, {}, {}, [protocol, typedAmount]);

    wrapper.findComponent(PillNarrowList).vm.$emit('example', '>100');
    await nextTick();

    expect(wrapper.findComponent(PillNarrowList).props('suggestions')[0]).toMatchObject({ kind: 'filter' });
  });
  // Picking a field and then thinking better of it used to leave an empty pill: it filters
  // nothing, shows nothing, and the only way out was to find its remove button.
  it('should drop a pill whose editor closed without a value', async () => {
    const wrapper = createWrapper();
    wrapper.findComponent(PillMenu).vm.$emit('select', protocol);
    await nextTick();
    await nextTick();
    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(1);

    wrapper.findComponent(PillValueEditor).vm.$emit('close');
    // Two ticks: the decision waits for the render on which a debounced editor commits.
    await nextTick();
    await nextTick();

    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(0);
  });

  // The pill and its editor are gone, so focus would otherwise fall to the document body and the
  // next keystroke would go nowhere. The bar is where the user still is.
  it('should put the caret back in the input after dropping a pill', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] }, {}, {}, fields, { attachTo: document.body });

    wrapper.findComponent(FilterPill).vm.$emit('remove');
    await nextTick();
    await nextTick();

    expect(document.activeElement).toBe(wrapper.get('[data-testid=pill-narrow-input]').element);
    wrapper.unmount();
  });

  it('should keep a pill whose editor closed with a value', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] });

    wrapper.findComponent(PillValueEditor).vm.$emit('close');
    await nextTick();

    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(1);
  });

  // The pill survives, so nothing was dropped and the drop path's focus restore never runs. The
  // editor that held focus has still unmounted, and `RuiMenu` will not hand focus back because
  // `disable-auto-focus` governs both directions and the bar needs it for the open one.
  it('should put the caret back in the input after an editor closes with its value kept', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] }, {}, {}, fields, { attachTo: document.body });

    wrapper.findComponent(PillValueEditor).vm.$emit('close');
    await nextTick();
    await nextTick();

    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(1);
    expect(document.activeElement).toBe(wrapper.get('[data-testid=pill-narrow-input]').element);
    wrapper.unmount();
  });

  // `Clear all` is rendered only while filters exist, so pressing it removes the very button that
  // holds focus.
  it('should put the caret back in the input after clearing every filter', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] }, {}, {}, fields, { attachTo: document.body });

    await wrapper.get('[data-testid=pill-clear]').trigger('click');
    await nextTick();
    await nextTick();

    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(0);
    expect(document.activeElement).toBe(wrapper.get('[data-testid=pill-narrow-input]').element);
    wrapper.unmount();
  });
  // The debounced editors commit what they hold when they unmount, which happens a render after
  // the pill is removed: without the guard the pill came straight back.
  it('should not let a closing editor resurrect the pill that was just removed', async () => {
    const wrapper = createWrapper({ protocols: ['aave'] });

    wrapper.findComponent(FilterPill).vm.$emit('remove');
    // Exactly what an editor's `onBeforeUnmount` does, in the same tick as the removal.
    wrapper.findComponent(PillValueEditor).vm.$emit('update', {
      fieldKey: 'protocols',
      op: 'is',
      values: ['aave'],
    });
    await nextTick();

    expect(wrapper.findAllComponents(FilterPill)).toHaveLength(0);
    expect(lastEmit(wrapper, 'update:matches')).toStrictEqual({});
  });

  // A free-text editor commits through a debounce, so remembering on every update stored `swap`,
  // `swap on`, … as separate values, each one writing the whole settings blob.
  it('should remember a free-text value once, when its editor closes', async () => {
    const notes: FieldDef = {
      allowExclusion: false,
      binding: { kind: 'filter' },
      freeText: true,
      key: 'notesSubstring',
      label: 'Notes',
      multiple: false,
      operators: ['is'],
      valueType: 'enum',
    };
    const wrapper = createWrapper({ notesSubstring: 'sw' }, {}, {}, [notes]);
    updateFrontendSetting.mockClear();
    const remembered = (): string[] =>
      updateFrontendSetting.mock.calls.at(-1)?.[0].recentFilterValues.notesSubstring?.map(entry => entry.value) ?? [];

    const editor = wrapper.findComponent(PillValueEditor);
    editor.vm.$emit('update', { fieldKey: 'notesSubstring', op: 'is', values: ['swap'] });
    editor.vm.$emit('update', { fieldKey: 'notesSubstring', op: 'is', values: ['swap on'] });
    await nextTick();
    expect(updateFrontendSetting).not.toHaveBeenCalled();

    editor.vm.$emit('close');
    await nextTick();
    await nextTick();

    expect(remembered()).toStrictEqual(['swap on']);
  });
});
