"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

const INTERVAL_MS = 3000;

export function CasePolling() {
  const router = useRouter();
  useEffect(() => {
    const t = setInterval(() => router.refresh(), INTERVAL_MS);
    return () => clearInterval(t);
  }, [router]);
  return null;
}
