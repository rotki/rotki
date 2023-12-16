type BackoffCall<T> = () => Promise<T>;

export function wait(duration: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, duration));
}

export async function backoff<T>(retries: number, call: BackoffCall<T>, delay = 5000): Promise<T> {
  let result: T;
  try {
    result = await call();
  }
  catch (error) {
    if (retries > 1) {
      await wait(delay);
      result = await backoff(retries - 1, call, delay * 2);
    }
    else {
      throw error;
    }
  }
  return result;
}
