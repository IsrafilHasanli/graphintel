import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { useId } from "react";
import { cx } from "@/lib/format";

const baseControl =
  "w-full rounded-md border border-surface-border bg-surface-panel px-3 py-2 text-sm text-slate-100 " +
  "placeholder:text-slate-500 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand";

export function Label({
  htmlFor,
  children,
  className,
}: {
  htmlFor: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={cx("mb-1 block text-xs font-medium text-slate-300", className)}
    >
      {children}
    </label>
  );
}

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function TextInput({ label, id, className, ...rest }: TextInputProps) {
  const generated = useId();
  const inputId = id ?? generated;
  return (
    <div>
      {label ? <Label htmlFor={inputId}>{label}</Label> : null}
      <input id={inputId} className={cx(baseControl, className)} {...rest} />
    </div>
  );
}

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function TextArea({ label, id, className, ...rest }: TextAreaProps) {
  const generated = useId();
  const inputId = id ?? generated;
  return (
    <div>
      {label ? <Label htmlFor={inputId}>{label}</Label> : null}
      <textarea
        id={inputId}
        className={cx(baseControl, "resize-y", className)}
        {...rest}
      />
    </div>
  );
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  children: ReactNode;
}

export function Select({ label, id, className, children, ...rest }: SelectProps) {
  const generated = useId();
  const inputId = id ?? generated;
  return (
    <div>
      {label ? <Label htmlFor={inputId}>{label}</Label> : null}
      <select id={inputId} className={cx(baseControl, className)} {...rest}>
        {children}
      </select>
    </div>
  );
}
