import type { AxiosResponse } from 'axios';

export function downloadFileByUrl(url: string, fileName: string): void {
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', fileName);
  if (document.createEvent) {
    const event = document.createEvent('MouseEvents');
    event.initEvent('click', true, true);
    link.dispatchEvent(event);
  }
  else {
    link.click();
  }
}

export function downloadFileByBlobResponse(response: AxiosResponse, filename: string): void {
  const url = window.URL.createObjectURL(response.request.response);
  downloadFileByUrl(url, filename);
}

export function downloadFileByTextContent(
  text: string,
  filename: string,
  type: 'text/plain' | 'application/json' | 'text/csv' = 'text/plain',
): void {
  const file = new Blob([text], {
    type,
  });
  const url = window.URL.createObjectURL(file);
  downloadFileByUrl(url, filename);
}
