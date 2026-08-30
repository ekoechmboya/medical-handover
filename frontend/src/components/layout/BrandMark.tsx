export default function BrandMark({
  className = "h-8 w-8",
}: {
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <rect width="40" height="40" rx="11" fill="var(--color-brand-700)" />
      <path
        d="M13 20.5c2.4 2.1 4.9 2.1 7.3 0 2.4 2.1 4.9 2.1 7.3 0"
        stroke="white"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      <circle cx="20" cy="14.2" r="3" fill="white" />
      <path
        d="M14.6 28.4c1.5-1.3 3.3-1.3 4.8 0 1.5-1.3 3.3-1.3 4.8 0"
        stroke="white"
        strokeWidth="2.2"
        strokeLinecap="round"
        opacity="0.75"
      />
    </svg>
  );
}