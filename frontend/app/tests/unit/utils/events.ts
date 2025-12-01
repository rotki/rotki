import { vi } from 'vitest';

export function createClipboardEvent(text: string): ClipboardEvent {
  const clipboardData = {
    getData: vi.fn().mockReturnValue(text),
    setData: vi.fn(),
    clearData: vi.fn(),
    types: ['text/plain'],
    files: [] as unknown as FileList,
    items: [] as unknown as DataTransferItemList,
  };

  const event = new Event('paste', {
    bubbles: true,
    cancelable: true,
  }) as ClipboardEvent;

  Object.defineProperty(event, 'clipboardData', {
    value: clipboardData,
    writable: false,
  });

  return event;
}
