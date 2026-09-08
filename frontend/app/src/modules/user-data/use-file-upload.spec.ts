import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  checkFiles,
  formatFileFilter,
  isValidFile,
  useFileUploadFeedback,
} from '@/modules/user-data/use-file-upload';

function file(name: string, type = ''): File {
  return new File(['content'], name, { type });
}

describe('isValidFile', () => {
  it('should accept a file whose extension is listed', () => {
    expect(isValidFile(file('accounts.csv'), '.csv')).toBe(true);
  });

  it('should accept a file whose mime type is listed', () => {
    expect(isValidFile(file('accounts', 'text/csv'), 'text/csv')).toBe(true);
  });

  /** A browser reports no type for some files, so the extension has to be enough on its own. */
  it('should accept a listed extension even when the browser reports no type', () => {
    expect(isValidFile(file('accounts.csv', ''), '.csv')).toBe(true);
  });

  it('should ignore the case of the extension', () => {
    expect(isValidFile(file('ACCOUNTS.CSV'), '.csv')).toBe(true);
  });

  it('should accept any image for the image wildcard', () => {
    expect(isValidFile(file('logo.png', 'image/png'), 'image/*')).toBe(true);
  });

  it('should not treat the image wildcard as accepting everything', () => {
    expect(isValidFile(file('accounts.csv', 'text/csv'), 'image/*')).toBe(false);
  });

  it('should accept a file matching any entry in a list', () => {
    expect(isValidFile(file('report.json', 'application/json'), '.csv, .json')).toBe(true);
  });

  it('should ignore the spaces around a list entry', () => {
    expect(isValidFile(file('report.json'), '.csv,  .json  ')).toBe(true);
  });

  it('should reject a file that matches neither extension nor type', () => {
    expect(isValidFile(file('archive.zip', 'application/zip'), '.csv')).toBe(false);
  });

  /**
   * Only `image/*` is understood; every other wildcard is compared as text, so a file is rejected
   * rather than silently let through by a filter that looks like it should match.
   */
  it('should not expand a wildcard other than image', () => {
    expect(isValidFile(file('notes.txt', 'text/plain'), 'text/*')).toBe(false);
  });

  it('should reject a file with no extension against an extension filter', () => {
    expect(isValidFile(file('accounts'), '.csv')).toBe(false);
  });
});

describe('checkFiles', () => {
  it('should return the file when exactly one valid file is given', () => {
    const picked = file('accounts.csv');

    expect(checkFiles([picked], '.csv')).toEqual({ file: picked, valid: true });
  });

  it('should refuse more than one file', () => {
    expect(checkFiles([file('a.csv'), file('b.csv')], '.csv')).toEqual({ reason: 'many-files', valid: false });
  });

  it('should refuse an empty selection', () => {
    expect(checkFiles([], '.csv')).toEqual({ reason: 'many-files', valid: false });
  });

  it('should refuse a file of the wrong type', () => {
    expect(checkFiles([file('archive.zip')], '.csv')).toEqual({ reason: 'wrong-type', valid: false });
  });
});

describe('formatFileFilter', () => {
  it('should drop the dots and space the list out', () => {
    expect(formatFileFilter('.csv,.json')).toBe('csv, json');
  });

  it('should leave a mime type alone', () => {
    expect(formatFileFilter('text/csv')).toBe('text/csv');
  });

  it('should trim the entries', () => {
    expect(formatFileFilter(' .csv , .json ')).toBe('csv, json');
  });
});

describe('useFileUploadFeedback', () => {
  const removeFile = vi.fn();
  const onErrorCleared = vi.fn();
  const onUploadedCleared = vi.fn();

  function createFeedback(): ReturnType<typeof useFileUploadFeedback> {
    return useFileUploadFeedback({ onErrorCleared, onUploadedCleared, removeFile });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('showing an error', () => {
    it('should show the message and drop the picked file', () => {
      const { error, showError } = createFeedback();

      showError('too many');

      expect(get(error)).toBe('too many');
      expect(removeFile).toHaveBeenCalledOnce();
    });

    it('should clear the error after four seconds', async () => {
      const { error, showError } = createFeedback();

      showError('too many');
      await vi.advanceTimersByTimeAsync(4000);

      expect(get(error)).toBe('');
      expect(onErrorCleared).toHaveBeenCalled();
    });

    it('should keep the error until then', async () => {
      const { error, showError } = createFeedback();

      showError('too many');
      await vi.advanceTimersByTimeAsync(3999);

      expect(get(error)).toBe('too many');
    });

    /** Without cancelling the first timer the earlier error clears the later one four seconds in. */
    it('should restart the countdown when a second error replaces the first', async () => {
      const { error, showError } = createFeedback();

      showError('first');
      await vi.advanceTimersByTimeAsync(3000);
      showError('second');
      await vi.advanceTimersByTimeAsync(3000);

      expect(get(error)).toBe('second');
    });

    it('should clear instead of showing when the message is empty', () => {
      const { error, showError } = createFeedback();

      showError('');

      expect(get(error)).toBe('');
      expect(onErrorCleared).toHaveBeenCalledOnce();
      expect(removeFile).not.toHaveBeenCalled();
    });
  });

  describe('acknowledging an upload', () => {
    it('should drop the picked file when the upload lands', () => {
      const { acknowledgeUpload } = createFeedback();

      acknowledgeUpload(true);

      expect(removeFile).toHaveBeenCalledOnce();
    });

    it('should lower the flag after four seconds', async () => {
      const { acknowledgeUpload } = createFeedback();

      acknowledgeUpload(true);
      await vi.advanceTimersByTimeAsync(4000);

      expect(onUploadedCleared).toHaveBeenCalledOnce();
    });

    it('should do nothing when the flag goes down', async () => {
      const { acknowledgeUpload } = createFeedback();

      acknowledgeUpload(false);
      await vi.advanceTimersByTimeAsync(4000);

      expect(removeFile).not.toHaveBeenCalled();
      expect(onUploadedCleared).not.toHaveBeenCalled();
    });
  });

  describe('the two kinds of feedback replacing each other', () => {
    it('should not clear an error raised after an upload was acknowledged', async () => {
      const { acknowledgeUpload, error, showError } = createFeedback();

      acknowledgeUpload(true);
      await vi.advanceTimersByTimeAsync(3000);
      showError('failed');
      await vi.advanceTimersByTimeAsync(1500);

      expect(get(error)).toBe('failed');
      expect(onUploadedCleared).not.toHaveBeenCalled();
    });

    it('should give the acknowledgement its full four seconds after an error', async () => {
      const { acknowledgeUpload, showError } = createFeedback();

      showError('failed');
      await vi.advanceTimersByTimeAsync(3000);
      acknowledgeUpload(true);
      await vi.advanceTimersByTimeAsync(1500);

      expect(onUploadedCleared).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(2500);

      expect(onUploadedCleared).toHaveBeenCalledOnce();
    });
  });
});
