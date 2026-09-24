import type { StubInstance } from '@test/utils/component-vm';
import { mount, type VueWrapper } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { DateFormat } from '@/modules/core/common/date-format';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const submitTask = vi.fn();
const useIsActive = vi.fn();
const getPath = vi.fn();
const importFile = vi.fn();
const importDataFrom = vi.fn();
const resolveLocations = vi.fn();
const rememberAliases = vi.fn();

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
    importDataFrom,
    importFile,
  })),
}));

vi.mock('@/modules/user-data/use-import-location-mapping', () => ({
  useImportLocationMapping: vi.fn().mockImplementation(() => ({
    cancelMappings: vi.fn(),
    confirmMappings: vi.fn(),
    pending: ref(),
    rememberAliases,
    resolveLocations,
  })),
}));

const ImportSource = (await import('@/modules/user-data/ImportSource.vue')).default;

/** Declares the two props the upload outcome is read through, which `inputStub` does not carry. */
const fileUploadStub: Record<string, unknown> = {
  emits: ['update:modelValue', 'update:errorMessage', 'update:uploaded'],
  name: 'FileUpload',
  props: ['modelValue', 'errorMessage', 'uploaded', 'loading', 'source'],
  template: '<div />',
};

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
    useIsActive.mockReturnValue(computed<boolean>(() => false));
    rememberAliases.mockResolvedValue(undefined);
    getPath.mockReturnValue(undefined);
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(): VueWrapper<InstanceType<typeof ImportSource>> {
    return mount(ImportSource, {
      global: {
        stubs: {
          DateFormatHelp: true,
          FileUpload: fileUploadStub,
          ImportLocationMappingDialog: true,
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

  async function attachFile(): Promise<void> {
    wrapper.findComponent<StubInstance>({ name: 'FileUpload' }).vm.$emit('update:modelValue', new File(['a'], 'a.csv'));
    await vi.advanceTimersToNextTimerAsync();
  }

  async function enableCustomFormat(): Promise<void> {
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

  it('should mark the upload done only when the task reports a completed import', async () => {
    submitTask.mockResolvedValue(ok(true));
    wrapper = createWrapper();
    await attachFile();

    await wrapper.find('form').trigger('submit');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.findComponent<StubInstance>({ name: 'FileUpload' }).props('uploaded')).toBe(true);
  });

  it('should leave the upload undone when the task settles on a failed import', async () => {
    submitTask.mockResolvedValue(ok(false));
    wrapper = createWrapper();
    await attachFile();

    await wrapper.find('form').trigger('submit');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.findComponent<StubInstance>({ name: 'FileUpload' }).props('uploaded')).toBe(false);
  });

  it('should surface an actionable task error on the upload field', async () => {
    submitTask.mockResolvedValue(err(TaskFailed({ message: 'bad csv' })));
    wrapper = createWrapper();
    await attachFile();

    await wrapper.find('form').trigger('submit');
    await vi.advanceTimersToNextTimerAsync();

    const upload = wrapper.findComponent<StubInstance>({ name: 'FileUpload' });
    expect(upload.props('uploaded')).toBe(false);
    expect(upload.props('errorMessage')).toBe('bad csv');
  });

  it('should hide both switches for a rotki custom import', async () => {
    wrapper = mount(ImportSource, {
      global: {
        stubs: {
          DateFormatHelp: true,
          FileUpload: fileUploadStub,
          ImportLocationMappingDialog: true,
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

    expect(field('import-date-format-switch').exists()).toBe(false);
    expect(wrapper.find('[data-testid=import-timezone-switch]').exists()).toBe(false);
  });

  describe('a rotki generic import', () => {
    function createRotkiWrapper(): VueWrapper<InstanceType<typeof ImportSource>> {
      return mount(ImportSource, {
        global: { stubs: { DateFormatHelp: true, FileUpload: fileUploadStub, ImportLocationMappingDialog: true } },
        props: { source: 'rotki_events' },
      });
    }

    async function submitFile(): Promise<void> {
      await attachFile();
      await wrapper.find('form').trigger('submit');
      await vi.advanceTimersToNextTimerAsync();
    }

    it('should import with the locations the user mapped, then save the chosen aliases', async () => {
      resolveLocations.mockResolvedValue({ mappings: { 'My old exchange': 'custom:old' }, proceed: true });
      submitTask.mockResolvedValue(ok(true));
      importFile.mockResolvedValue({ taskId: 1 });
      wrapper = createRotkiWrapper();
      await submitFile();

      expect(resolveLocations).toHaveBeenCalledWith('rotki_events', { file: expect.any(File) });
      await submitTask.mock.calls[0][0].run({ runTask: async (task: () => Promise<unknown>) => ok(await task()) });
      const data: unknown = importFile.mock.calls[0][0];
      assert(data instanceof FormData);
      expect(data.get('location_mappings')).toBe('{"My old exchange":"custom:old"}');
      expect(rememberAliases).toHaveBeenCalledOnce();
    });

    it('should not import when the user leaves the locations unmapped', async () => {
      resolveLocations.mockResolvedValue({ proceed: false });
      wrapper = createRotkiWrapper();
      await submitFile();

      expect(submitTask).not.toHaveBeenCalled();
      expect(rememberAliases).not.toHaveBeenCalled();
    });

    it('should show why the locations could not be checked', async () => {
      resolveLocations.mockResolvedValue({ error: 'Could not read the file', proceed: false });
      wrapper = createRotkiWrapper();
      await submitFile();

      expect(wrapper.findComponent<StubInstance>({ name: 'FileUpload' }).props('errorMessage')).toBe('Could not read the file');
    });

    it('should resolve and import a file read from disk by its path, with the mapped locations', async () => {
      getPath.mockReturnValue('/home/user/events.csv');
      resolveLocations.mockResolvedValue({ mappings: { luno: 'custom:luno' }, proceed: true });
      submitTask.mockResolvedValue(ok(true));
      importDataFrom.mockResolvedValue({ taskId: 1 });
      wrapper = createRotkiWrapper();
      await submitFile();

      expect(resolveLocations).toHaveBeenCalledWith('rotki_events', { path: '/home/user/events.csv' });
      await submitTask.mock.calls[0][0].run({ runTask: async (task: () => Promise<unknown>) => ok(await task()) });
      expect(importDataFrom).toHaveBeenCalledExactlyOnceWith({
        file: '/home/user/events.csv',
        locationMappings: '{"luno":"custom:luno"}',
        source: 'rotki_events',
        timestampFormat: null,
        timezone: null,
      });
      expect(importFile).not.toHaveBeenCalled();
    });

    it('should leave the mappings out of a path import whose locations all resolved', async () => {
      getPath.mockReturnValue('/home/user/events.csv');
      resolveLocations.mockResolvedValue({ mappings: {}, proceed: true });
      submitTask.mockResolvedValue(ok(true));
      importDataFrom.mockResolvedValue({ taskId: 1 });
      wrapper = createRotkiWrapper();
      await submitFile();

      await submitTask.mock.calls[0][0].run({ runTask: async (task: () => Promise<unknown>) => ok(await task()) });
      expect(importDataFrom.mock.calls[0][0]).not.toHaveProperty('locationMappings');
    });

    it('should keep the import done but say so when the chosen aliases could not be saved', async () => {
      resolveLocations.mockResolvedValue({ mappings: { luno: 'custom:luno' }, proceed: true });
      submitTask.mockResolvedValue(ok(true));
      rememberAliases.mockRejectedValue(new Error('Location custom:luno is archived'));
      wrapper = createRotkiWrapper();
      await submitFile();
      await vi.advanceTimersToNextTimerAsync();

      const upload = wrapper.findComponent<StubInstance>({ name: 'FileUpload' });
      expect(upload.props('uploaded')).toBe(true);
      expect(upload.props('errorMessage')).toBe('import_data.location_mapping.alias_error::Location custom:luno is archived');
    });
  });
});
