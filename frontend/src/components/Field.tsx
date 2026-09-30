import type { InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string };

export default function Field({ label, hint, id, ...input }: Props) {
  const inputId = id ?? input.name;
  const hintId = hint ? `${inputId}-hint` : undefined;
  return (
    <div className="field">
      <label className="field__label" htmlFor={inputId}>{label}</label>
      <input id={inputId} aria-describedby={hintId} {...input} />
      {hint && <span className="field__hint" id={hintId}>{hint}</span>}
    </div>
  );
}
