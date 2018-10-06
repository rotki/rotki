interface JQuery {
    pulsate(action: string | PulsateOptions): void;

    datetimepicker(options?: DateTimePickerOptions): JQuery;

    multiSelect(option: string | MultiSelectOptions, options?: MultiSelectOptions | any): void;
}

interface DateTimePickerOptions {
    format?: string;
    timepicker?: boolean;
}

// noinspection JSUnusedGlobalSymbols
interface JQueryStatic {
    confirm(options?: ConfirmOptions): void;

    alert(options?: AlertOptions | string | Alert): void;
}

interface MultiSelectOptions {
    value?: string;
    symbol?: string;
    selectableHeader?: string;
    selectionHeader?: string;
    afterSelect?: (values: any) => void;
    afterDeselect?: (values: any) => void;
    afterInit?: (container: any) => void;
}


interface AlertOptions {
    content: () => void;
}

interface Alert {
    buttons?: { [name: string]: { action: () => void } };

    setType(type: string): void;

    setTitle(title: string): void;

    setContentAppend(content: string): void;
}

interface PulsateOptions {
    color?: string;     // set the color of the pulse
    reach?: number;     // how far the pulse goes in px
    speed?: number;     // how long one pulse takes in ms
    pause?: number;     // how long the pause between pulses is in ms
    glow?: boolean;     // if the glow should be shown too
    repeat?: boolean;   // will repeat forever if true, if given a number will repeat for that many times
    onHover?: boolean;  // if true only pulsate if user hovers over the element
}

interface ConfirmOptions {
    title?: string;
    content?: string;
    type?: string;
    typeAnimated?: true;
    buttons?: { [button: string]: ConfirmButton | (() => void) };
    onContentReady?: () => void;
}

interface ConfirmButton {
    text?: string;
    btnClass?: string;
    action?: () => void | boolean;
}
