import type { ComponentPublicInstance } from 'vue';
import type { Tag } from '@/modules/tags/tags';
import { invertColor } from '@rotki/common';
import { type DOMWrapper, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

vi.mock('@rotki/common', async importOriginal => ({
  ...await importOriginal<typeof import('@rotki/common')>(),
  randomColor: vi.fn<() => string>().mockReturnValue('123456'),
}));

const TagForm = (await import('@/modules/tags/TagForm.vue')).default;

describe('tagForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof TagForm>>;

  const baseModel = (): Tag => ({
    backgroundColor: 'ffffff',
    description: 'a description',
    foregroundColor: '000000',
    name: 'a tag',
  });

  beforeEach(() => {
    // The tag preview renders a TagIcon, which reads a display setting from the store.
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(modelValue: Tag = baseModel()): VueWrapper<InstanceType<typeof TagForm>> {
    return mount(TagForm, { props: { modelValue, stateUpdated: false } });
  }

  function field(testId: string): DOMWrapper<HTMLInputElement> {
    return wrapper.find<HTMLInputElement>(`[data-testid=${testId}] input`);
  }

  function nameMessages(): string[] {
    const name = wrapper.findComponent<ComponentPublicInstance<Record<string, unknown>>>('[data-testid=tag-creator-name]');
    const value: unknown = name.props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  function lastModel(): Tag {
    const updates = wrapper.emitted<[Tag]>('update:modelValue');
    expect(updates).toBeTruthy();
    return updates!.at(-1)![0];
  }

  it('should pass validation when the name is filled', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should fail validation when the name is empty', async () => {
    wrapper = createWrapper({ ...baseModel(), name: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should treat a whitespace-only name as empty', async () => {
    wrapper = createWrapper({ ...baseModel(), name: '   ' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should not require a description, its placeholder being no rule', async () => {
    wrapper = createWrapper({ ...baseModel(), description: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ ...baseModel(), name: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(nameMessages()).toEqual([]);
  });

  it('should reveal the name message once validate runs', async () => {
    wrapper = createWrapper({ ...baseModel(), name: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(nameMessages()).toEqual(['tag_creator.validation.empty_name']);
  });

  it('should show the name message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await field('tag-creator-name').setValue('');
    await vi.advanceTimersToNextTimerAsync();

    expect(nameMessages()).toEqual(['tag_creator.validation.empty_name']);
  });

  it('should write a name edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await field('tag-creator-name').setValue('renamed');
    await vi.advanceTimersToNextTimerAsync();

    expect(lastModel().name).toBe('renamed');
  });

  it('should trim a description on the way into the model, choosing between "" and null', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await field('tag-creator-description').setValue('  padded  ');
    await vi.advanceTimersToNextTimerAsync();

    expect(lastModel().description).toBe('padded');
  });

  it('should write a blank description into the model as null', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await field('tag-creator-description').setValue('   ');
    await vi.advanceTimersToNextTimerAsync();

    expect(lastModel().description).toBeNull();
  });

  it('should show a null description as an empty field', async () => {
    wrapper = createWrapper({ ...baseModel(), description: null });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('tag-creator-description').element.value).toBe('');
  });

  it('should replace both colours when shuffled', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.findComponent({ name: 'RuiButton' }).trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    const model = lastModel();
    expect(model.backgroundColor).toBe('123456');
    expect(model.foregroundColor?.toLowerCase()).toBe(invertColor('123456').toLowerCase());
    expect(model.name).toBe('a tag');
  });

  it('should flag stateUpdated when only a colour is shuffled, which no rule validates', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    await wrapper.findComponent({ name: 'RuiButton' }).trigger('click');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });
});
