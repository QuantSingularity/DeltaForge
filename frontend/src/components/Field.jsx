// Labeled input used across the auth and settings forms.
export default function Field({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  autoComplete,
  required = true,
  error,
}) {
  return (
    <label className="block">
      <span className="eyebrow">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={required}
        className={`mt-1 w-full bg-panel-850 border rounded-md px-3 py-2 text-sm outline-none transition-colors ${
          error
            ? "border-sell/60 focus:border-sell"
            : "border-panel-700 focus:border-ember/60"
        }`}
      />
    </label>
  );
}
