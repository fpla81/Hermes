import Link from "next/link";

export function Brand({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const dims =
    size === "sm" ? "h-7 w-7 text-sm" : size === "lg" ? "h-12 w-12 text-2xl" : "h-9 w-9 text-base";
  const text =
    size === "sm" ? "text-base" : size === "lg" ? "text-3xl" : "text-lg";
  return (
    <Link href="/cases" className="flex items-center gap-2.5">
      <span
        className={`grid place-items-center rounded-md bg-primary font-serif font-semibold text-primary-foreground shadow-sm ${dims}`}
      >
        H
      </span>
      <span className={`font-serif font-semibold tracking-tight ${text}`}>
        Hermes
      </span>
    </Link>
  );
}
