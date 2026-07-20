import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCustomBackend } from './use-custom-backend';

const { deleteBackendUrl, getBackendUrl, saveBackendUrl } = vi.hoisted(() => ({
  deleteBackendUrl: vi.fn(),
  getBackendUrl: vi.fn(() => ({ sessionOnly: false, url: '' })),
  saveBackendUrl: vi.fn(),
}));

vi.mock('@/modules/auth/account-management', () => ({
  deleteBackendUrl,
  getBackendUrl,
  saveBackendUrl,
}));

describe('modules/auth/login/useCustomBackend', () => {
  let onChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    getBackendUrl.mockReturnValue({ sessionOnly: false, url: '' });
    onChange = vi.fn();
  });

  it('should start collapsed with no override', () => {
    const { display, modelSessionOnly, modelUrl, saved } = useCustomBackend({ onChange });

    expect(get(display)).toBe(false);
    expect(get(saved)).toBe(false);
    expect(get(modelUrl)).toBe('');
    expect(get(modelSessionOnly)).toBe(false);
  });

  it('should hydrate the form from a persisted override', () => {
    getBackendUrl.mockReturnValue({ sessionOnly: true, url: 'http://localhost:9001' });
    const { loadBackendSettings, modelSessionOnly, modelUrl, saved } = useCustomBackend({ onChange });

    loadBackendSettings();

    expect(get(modelUrl)).toBe('http://localhost:9001');
    expect(get(modelSessionOnly)).toBe(true);
    expect(get(saved)).toBe(true);
  });

  it('should not mark as saved when no url is persisted', () => {
    const { loadBackendSettings, saved } = useCustomBackend({ onChange });

    loadBackendSettings();

    expect(get(saved)).toBe(false);
  });

  it('should persist the url, notify the caller and collapse on save', () => {
    const { display, modelSessionOnly, modelUrl, saveBackend, saved, toggleDisplay } = useCustomBackend({ onChange });

    toggleDisplay();
    set(modelUrl, 'http://localhost:9001');
    set(modelSessionOnly, true);
    saveBackend();

    expect(saveBackendUrl).toHaveBeenCalledWith({ sessionOnly: true, url: 'http://localhost:9001' });
    expect(onChange).toHaveBeenCalledWith('http://localhost:9001');
    expect(get(saved)).toBe(true);
    expect(get(display)).toBe(false);
  });

  it('should delete the override, notify with null and collapse on clear', () => {
    getBackendUrl.mockReturnValue({ sessionOnly: true, url: 'http://localhost:9001' });
    const { clearBackend, display, loadBackendSettings, modelSessionOnly, modelUrl, saved } = useCustomBackend({ onChange });

    loadBackendSettings();
    clearBackend();

    expect(deleteBackendUrl).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(null);
    expect(get(modelUrl)).toBe('');
    expect(get(modelSessionOnly)).toBe(false);
    expect(get(saved)).toBe(false);
    expect(get(display)).toBe(false);
  });

  it('should expand and collapse the panel on toggle', () => {
    const { display, toggleDisplay } = useCustomBackend({ onChange });

    toggleDisplay();
    expect(get(display)).toBe(true);

    toggleDisplay();
    expect(get(display)).toBe(false);
  });

  it('should tint the server icon primary while the override is session-only', () => {
    const { modelSessionOnly, serverColor } = useCustomBackend({ onChange });

    set(modelSessionOnly, true);

    expect(get(serverColor)).toBe('primary');
  });

  it('should tint the server icon success once the override is persisted', () => {
    getBackendUrl.mockReturnValue({ sessionOnly: false, url: 'http://localhost:9001' });
    const { loadBackendSettings, serverColor } = useCustomBackend({ onChange });

    loadBackendSettings();

    expect(get(serverColor)).toBe('success');
  });

  it('should prefer the session-only tint over the persisted one', () => {
    getBackendUrl.mockReturnValue({ sessionOnly: true, url: 'http://localhost:9001' });
    const { loadBackendSettings, serverColor } = useCustomBackend({ onChange });

    loadBackendSettings();

    expect(get(serverColor)).toBe('primary');
  });

  it('should leave the server icon untinted with no override', () => {
    const { serverColor } = useCustomBackend({ onChange });

    expect(get(serverColor)).toBeUndefined();
  });
});
