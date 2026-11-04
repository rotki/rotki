import type { StubInstance } from '@test/utils/component-vm';
import type { ActivityContext, NativeActivitySpec } from '@/modules/task-center/use-native-task';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { DateFormat } from '@/modules/core/common/date-format';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const submitTask = vi.fn();
const useIsActive = vi.fn();
const getPath = vi.fn();
const removeFile = vi.fn<() => void>();
const checkImportLocations = vi.fn();
const checkImportFileLocations = vi.fn();
const importDataFrom = vi.fn();
const importFile = vi.fn();

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn().mockImplementation(() => ({ submitTask })),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: vi.fn().mockImplementation(() => ({ useIsActive })),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn().mockImplementation(() => ({ getPath })),
}));

vi.mock('@/modules/user-data/use-import-data-api', () => ({
  useImportDataApi: vi.fn().mockImplementation(() => ({
    checkImportLocations,
    checkImportFileLocations,
    importDataFrom,
    importFile,
  })),
}));

const ImportSource = (await import('@/modules/user-data/ImportSource.vue')).default;

/**
 * The library uploader, declaring the two props the upload outcome is read through, which
 * `inputStub` does not carry, and exposing the reset the component calls after an import.
 */
const fileUploadStub = defineComponent({
  emits: ['update:modelValue', 'error'],
  name: 'RuiFileUpload',
  props: ['modelValue', 'errorMessages', 'uploaded', 'loading', 'accept'],
  setup(_props, { expose }) {
    expose({ removeFile });
    return {};
  },
  template: '<div />',
});

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

describe('importSource', () => {
  let wrapper: VueWrapper<InstanceType<typeof ImportSource>>;

  beforeEach(() => {
    vi.clearAllMocks();
    getPath.mockReturnValue(undefined);
    checkImportLocations.mockResolvedValue([]);
    checkImportFileLocations.mockResolvedValue([]);
    useIsActive.mockReturnValue(computed<boolean>(() => false));
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  function createWrapper(): VueWrapper<InstanceType<typeof ImportSource>> {
    return mount(ImportSource, {
      global: {
        stubs: {
          DateFormatHelp: true,
          ImportLocationMappings: true,
          RuiFileUpload: fileUploadStub,
          RuiSwitch: {
            emits: ['update:modelValue'],
            name: 'RuiSwitch',
            props: ['modelValue'],
            template: '<div><slot /></div>',
          },
          RuiTextField: inputStub('RuiTextField'),
          RuiTimezoneSelect: inputStub('RuiTimezoneSelect'),
        },
      },
      props: { source: 'cointracking' },
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(): string[] {
    const value: unknown = field('import-date-format').props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  function importDisabled(): unknown {
    return wrapper.findComponent<StubInstance>('[data-testid=button-import]').props('disabled');
  }

  function upload(): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>({ name: 'RuiFileUpload' });
  }

  async function attachFile(): Promise<void> {
    upload().vm.$emit('update:modelValue', new File(['a'], 'a.csv'));
    await vi.advanceTimersToNextTimerAsync();
  }

  async function submit(): Promise<void> {
    await wrapper.find('form').trigger('submit');
    await flushPromises();
  }

  async function openOptions(): Promise<void> {
    await wrapper.find('[data-testid=import-options-toggle]').trigger('click');
    await vi.advanceTimersToNextTimerAsync();
  }

  async function enableCustomFormat(): Promise<void> {
    await openOptions();
    field('import-date-format-switch').vm.$emit('update:modelValue', true);
    await vi.advanceTimersToNextTimerAsync();
  }

  async function typeFormat(value: string): Promise<void> {
    const input = field('import-date-format');
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should keep the import blocked until a file is chosen', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(importDisabled()).toBe(true);

    await attachFile();

    expect(importDisabled()).toBe(false);
  });

  it('should hide the format field until the switch is turned on', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(field('import-date-format').exists()).toBe(false);

    await enableCustomFormat();

    expect(field('import-date-format').props('modelValue')).toBe(DateFormat.DateMonthYearHourMinuteSecond);
  });

  it('should keep the parsing options folded until asked for', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(field('import-date-format-switch').exists()).toBe(false);

    await openOptions();

    expect(field('import-date-format-switch').exists()).toBe(true);
  });

  it('should count an option still in effect on the folded toggle', async () => {
    wrapper = createWrapper();
    await enableCustomFormat();

    await openOptions();

    const toggle = wrapper.find('[data-testid=import-options-toggle]');
    expect(toggle.attributes('aria-expanded')).toBe('false');
    expect(toggle.text()).toContain('import_data.parsing_options_active');
  });

  it('should accept the default format the switch seeds', async () => {
    wrapper = createWrapper();
    await attachFile();
    await enableCustomFormat();

    expect(messages()).toEqual([]);
    expect(importDisabled()).toBe(false);
  });

  it('should reject a pattern with no recognised directive', async () => {
    wrapper = createWrapper();
    await attachFile();
    await enableCustomFormat();

    await typeFormat('not a date');

    expect(messages()).toEqual(['general_settings.date_display.validation.invalid']);
    expect(importDisabled()).toBe(true);
  });

  it('should report a blank pattern as invalid, never as empty', async () => {
    wrapper = createWrapper();
    await attachFile();
    await enableCustomFormat();

    await typeFormat('');

    expect(messages()).toEqual(['general_settings.date_display.validation.invalid']);
    expect(importDisabled()).toBe(true);
  });

  it('should report a whitespace-only pattern as both empty and invalid', async () => {
    wrapper = createWrapper();
    await attachFile();
    await enableCustomFormat();

    await typeFormat('   ');

    expect(messages()).toEqual([
      'general_settings.date_display.validation.empty',
      'general_settings.date_display.validation.invalid',
    ]);
  });

  it('should reject a pattern while typing, before the field is left', async () => {
    wrapper = createWrapper();
    await attachFile();
    await enableCustomFormat();

    field('import-date-format').vm.$emit('update:modelValue', 'not a date');
    await vi.advanceTimersToNextTimerAsync();

    expect(messages()).toEqual(['general_settings.date_display.validation.invalid']);
  });

  it('should accept a pattern once a directive is typed back in', async () => {
    wrapper = createWrapper();
    await attachFile();
    await enableCustomFormat();

    await typeFormat('not a date');
    await typeFormat('%d/%m/%Y');

    expect(messages()).toEqual([]);
    expect(importDisabled()).toBe(false);
  });

  it('should stop validating once the switch is turned back off', async () => {
    wrapper = createWrapper();
    await attachFile();
    await enableCustomFormat();
    await typeFormat('not a date');

    field('import-date-format-switch').vm.$emit('update:modelValue', false);
    await vi.advanceTimersToNextTimerAsync();

    expect(field('import-date-format').exists()).toBe(false);
    expect(importDisabled()).toBe(false);
  });

  it('should not claim success for a non-boolean task result', async () => {
    submitTask.mockResolvedValue(ok({ locations: [] }));
    wrapper = createWrapper();
    await attachFile();
    await submit();

    expect(wrapper.find('[data-testid=import-complete]').exists()).toBe(false);
    expect(upload().props('uploaded')).toBe(false);
    expect(removeFile).not.toHaveBeenCalled();
  });

  it.each([undefined, '/tmp/a.csv'])('should require explicit mappings before importing a custom CSV with path %s', async (path) => {
    const resolutions = [{ value: 'luno', status: 'unresolved', location: null, candidates: [] }];
    checkImportLocations.mockResolvedValueOnce(resolutions).mockResolvedValueOnce([]);
    checkImportFileLocations.mockResolvedValueOnce(resolutions).mockResolvedValueOnce([]);
    const runTask = vi.fn().mockResolvedValue(ok(true));
    submitTask.mockImplementation(async (spec: NativeActivitySpec<boolean>) => spec.run(createMock<ActivityContext>({
      cancelled: () => false,
      runTask,
    })));
    getPath.mockReturnValue(path);
    wrapper = createWrapper();
    await wrapper.setProps({ source: 'rotki_events' });
    await attachFile();
    await submit();

    const mappings = wrapper.findComponent({ name: 'ImportLocationMappings' });
    expect(mappings.props('locations')).toEqual(resolutions);
    expect(runTask).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=import-complete]').exists()).toBe(false);

    mappings.vm.$emit('update:modelValue', { luno: 'external' });
    await submit();

    expect(runTask).toHaveBeenCalledOnce();
    expect(wrapper.find('[data-testid=import-complete]').exists()).toBe(true);
  });

  it('should send a packaged file preflight only the fields its endpoint accepts', async () => {
    submitTask.mockImplementation(async (spec: NativeActivitySpec<boolean>) => spec.run(createMock<ActivityContext>({
      cancelled: () => false,
      runTask: vi.fn().mockResolvedValue(ok(true)),
    })));
    getPath.mockReturnValue('/tmp/a.csv');
    wrapper = createWrapper();
    await wrapper.setProps({ source: 'rotki_events' });
    await attachFile();
    await submit();

    expect(checkImportLocations).toHaveBeenCalledExactlyOnceWith({
      file: '/tmp/a.csv',
      locationMappings: {},
      source: 'rotki_events',
    });
  });

  it('should mark the upload done only when the task reports a completed import', async () => {
    submitTask.mockResolvedValue(ok(true));
    wrapper = createWrapper();
    await attachFile();

    await submit();

    expect(upload().props('uploaded')).toBe(true);
    expect(wrapper.find('[data-testid=import-complete]').exists()).toBe(true);
  });

  it('should empty the uploader once the import completes', async () => {
    submitTask.mockResolvedValue(ok(true));
    wrapper = createWrapper();
    await attachFile();

    await submit();

    expect(removeFile).toHaveBeenCalledOnce();
  });

  it('should leave the upload undone when the task settles on a failed import', async () => {
    submitTask.mockResolvedValue(ok(false));
    wrapper = createWrapper();
    await attachFile();

    await submit();

    expect(upload().props('uploaded')).toBe(false);
    expect(wrapper.find('[data-testid=import-complete]').exists()).toBe(false);
  });

  it('should surface an actionable task error on the upload field and keep the file', async () => {
    submitTask.mockResolvedValue(err(TaskFailed({ message: 'bad csv' })));
    wrapper = createWrapper();
    await attachFile();

    await submit();

    expect(upload().props('uploaded')).toBe(false);
    expect(upload().props('errorMessages')).toEqual(['bad csv']);
    expect(removeFile).not.toHaveBeenCalled();
  });

  it('should drop the last error once another file is picked', async () => {
    submitTask.mockResolvedValue(err(TaskFailed({ message: 'bad csv' })));
    wrapper = createWrapper();
    await attachFile();
    await submit();

    await attachFile();

    expect(upload().props('errorMessages')).toEqual([]);
  });

  it('should drop the done mark once another file is picked', async () => {
    submitTask.mockResolvedValue(ok(true));
    wrapper = createWrapper();
    await attachFile();
    await submit();

    await attachFile();

    expect(upload().props('uploaded')).toBe(false);
  });

  it('should hide both switches for a rotki custom import', async () => {
    wrapper = mount(ImportSource, {
      global: {
        stubs: {
          DateFormatHelp: true,
          RuiFileUpload: fileUploadStub,
          RuiSwitch: {
            emits: ['update:modelValue'],
            name: 'RuiSwitch',
            props: ['modelValue'],
            template: '<div><slot /></div>',
          },
          RuiTextField: inputStub('RuiTextField'),
        },
      },
      props: { source: 'rotki_events' },
    });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('[data-testid=import-options-toggle]').exists()).toBe(false);
    expect(field('import-date-format-switch').exists()).toBe(false);
    expect(wrapper.find('[data-testid=import-timezone-switch]').exists()).toBe(false);
  });
});
