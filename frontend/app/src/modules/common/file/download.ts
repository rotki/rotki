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

export function downloadFileByBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
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
