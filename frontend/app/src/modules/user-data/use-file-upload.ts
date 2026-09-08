import type { Ref } from 'vue';

/** How long an error, or the uploaded acknowledgement, stays on screen. */
const FEEDBACK_TIMEOUT_MS = 4000;

/** Why a set of picked files cannot be used, or the single file that can. */
export type FileCheck =
  | { readonly valid: true; readonly file: File }
  | { readonly valid: false; readonly reason: 'many-files' | 'wrong-type' };

interface UseFileUploadFeedbackOptions {
  /** Drops the picked file. The input element belongs to the component, so it does this. */
  removeFile: () => void;
  /** Reports that the error is gone, which clears the message the parent passed in. */
  onErrorCleared: () => void;
  /** Reports that the acknowledgement is gone, which lowers the parent's uploaded flag. */
  onUploadedCleared: () => void;
}

interface UseFileUploadFeedbackReturn {
  /** The error being shown, empty when there is none. */
  error: Readonly<Ref<string>>;
  /** Shows an error, dropping the picked file; an empty message clears instead. */
  showError: (message: string) => void;
  /** Clears the error and tells the parent to drop the message that caused it. */
  clearError: () => void;
  /** Shows the upload as done for a moment, then lowers the flag. */
  acknowledgeUpload: (uploaded: boolean) => void;
}

/**
 * Whether a picked file satisfies the `accept` attribute.
 *
 * @remarks
 * `acceptString` is an `accept` attribute value, comma separated. A file matches on either its
 * extension or its MIME type, since a browser reports no type for some files and checking either
 * alone rejects files the user is allowed to pick. `image/*` is the one wildcard handled; other
 * `type/*` forms are compared literally and will not match.
 *
 * @param file - the file the user picked or dropped
 * @param acceptString - the `accept` attribute value to match against
 * @returns whether the file is one the input accepts
 */
export function isValidFile(file: File, acceptString: string): boolean {
  const fileName = file.name;
  const fileExtension = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
  const fileType = file.type;

  const acceptTypes = acceptString.split(',').map(type => type.trim().toLowerCase());

  return acceptTypes.some(type =>
    type === fileExtension || type === fileType || (type === 'image/*' && fileType.startsWith('image/')),
  );
}

/**
 * Decides whether a drop or a pick can be used, so the component only has to phrase the refusal.
 *
 * @param files - what the user dropped or picked, which a drop can make more than one of
 * @param fileFilter - the `accept` attribute value the file has to satisfy
 * @returns the single usable file, or why there is not one
 */
export function checkFiles(files: File[] | FileList, fileFilter: string): FileCheck {
  if (files.length !== 1)
    return { reason: 'many-files', valid: false };

  const file = files[0];
  if (!isValidFile(file, fileFilter))
    return { reason: 'wrong-type', valid: false };

  return { file, valid: true };
}

/**
 * The accepted types as the hint reads them: `.csv,.json` becomes `csv, json`.
 *
 * @param fileFilter - the `accept` attribute value
 * @returns the same list without the dots, comma separated
 */
export function formatFileFilter(fileFilter: string): string {
  return fileFilter
    .split(',')
    .map(item => item.trim().replace(/^\./, ''))
    .join(', ');
}

/**
 * The upload's transient feedback: an error, or the acknowledgement that a file went through.
 * Both drop the picked file and both clear themselves after a moment, and either one replaces
 * the other rather than the two overlapping.
 *
 * @param options - what the component does on the feedback's behalf
 * @returns the error being shown and the ways it changes
 */
export function useFileUploadFeedback(options: UseFileUploadFeedbackOptions): UseFileUploadFeedbackReturn {
  const { onErrorCleared, onUploadedCleared, removeFile } = options;

  const error = shallowRef<string>('');
  const errorTimeout = shallowRef<ReturnType<typeof setTimeout>>();
  const uploadedTimeout = shallowRef<ReturnType<typeof setTimeout>>();

  function cancel(timeout: Ref<ReturnType<typeof setTimeout> | undefined>): void {
    const pending = get(timeout);
    if (pending) {
      clearTimeout(pending);
      set(timeout, undefined);
    }
  }

  function clearError(): void {
    set(error, '');
    onErrorCleared();
  }

  function showError(message: string): void {
    if (!message) {
      clearError();
      return;
    }

    cancel(errorTimeout);
    cancel(uploadedTimeout);
    removeFile();
    set(error, message);
    set(errorTimeout, setTimeout(clearError, FEEDBACK_TIMEOUT_MS));
  }

  function acknowledgeUpload(uploaded: boolean): void {
    cancel(errorTimeout);
    cancel(uploadedTimeout);

    if (!uploaded)
      return;

    removeFile();
    set(uploadedTimeout, setTimeout(() => {
      onUploadedCleared();
    }, FEEDBACK_TIMEOUT_MS));
  }

  tryOnScopeDispose(() => {
    cancel(errorTimeout);
    cancel(uploadedTimeout);
  });

  return {
    acknowledgeUpload,
    clearError,
    error: readonly(error),
    showError,
  };
}
