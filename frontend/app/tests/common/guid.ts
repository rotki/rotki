export class Guid {
  private readonly value: string = this.empty;

  public static newGuid(): Guid {
    return new Guid(
      'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.trunc(Math.random() * 16);
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      })
    );
  }

  public static get empty(): string {
    return '00000000-0000-0000-0000-000000000000';
  }

  public get empty(): string {
    return Guid.empty;
  }

  public static isValid(str: string): boolean {
    const validRegex =
      /^[\da-f]{8}-[\da-f]{4}-[1-5][\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i;
    return validRegex.test(str);
  }

  constructor(value?: string) {
    if (value && Guid.isValid(value)) {
      this.value = value;
    }
  }

  public toString() {
    return this.value;
  }

  public toJSON(): string {
    return this.value;
  }
}
