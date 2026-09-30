import { useRef, type ClipboardEvent, type KeyboardEvent } from "react";

const LENGTH = 6;

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  invalid?: boolean;
}

/** Шесть ячеек для кода из письма: ввод цифр, Backspace, стрелки, вставка всего кода. */
export default function CodeInput({ value, onChange, disabled, invalid }: Props) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length: LENGTH }, (_, i) => value[i] ?? "");

  const focus = (i: number) => refs.current[Math.max(0, Math.min(LENGTH - 1, i))]?.focus();

  const setAt = (i: number, d: string) => {
    const next = digits.slice();
    next[i] = d;
    onChange(next.join("").slice(0, LENGTH));
  };

  const onKeyDown = (i: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (/^\d$/.test(e.key)) {
      e.preventDefault();
      setAt(i, e.key);
      focus(i + 1);
    } else if (e.key === "Backspace") {
      e.preventDefault();
      if (digits[i]) setAt(i, "");
      else if (i > 0) { setAt(i - 1, ""); focus(i - 1); }
    } else if (e.key === "ArrowLeft") { e.preventDefault(); focus(i - 1); }
    else if (e.key === "ArrowRight") { e.preventDefault(); focus(i + 1); }
  };

  const onPaste = (e: ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, LENGTH);
    if (!pasted) return;
    e.preventDefault();
    onChange(pasted);
    focus(pasted.length);
  };

  return (
    <div className={"code" + (invalid ? " code--invalid" : "")} role="group" aria-label="Код из письма">
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => { refs.current[i] = el; }}
          className="code__cell"
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          aria-label={`Цифра ${i + 1}`}
          maxLength={1}
          value={d}
          disabled={disabled}
          autoFocus={i === 0}
          onKeyDown={(e) => onKeyDown(i, e)}
          onPaste={onPaste}
          onChange={(e) => {
            // мобильные клавиатуры и автозаполнение кода из SMS/почты
            const only = e.target.value.replace(/\D/g, "");
            if (only.length > 1) { onChange(only.slice(0, LENGTH)); focus(only.length); }
            else if (only) { setAt(i, only); focus(i + 1); }
          }}
        />
      ))}
    </div>
  );
}
