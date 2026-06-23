"use client";

import Link, { useLinkStatus } from "next/link";

import { Button, type ButtonProps } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

/** Shows the shared spinner while THIS link's navigation is pending (Next 16). */
function NavSpinner() {
  const { pending } = useLinkStatus();
  return pending ? <Spinner /> : null;
}

/**
 * A Button that navigates via <Link> and shows a loading spinner during the page
 * transition — so navigation buttons get the same loading feedback as form buttons.
 * Consistent loading everywhere: users never click into silence.
 */
export function LinkButton({
  href,
  children,
  ...props
}: Omit<ButtonProps, "asChild"> & { href: string }) {
  return (
    <Button asChild {...props}>
      <Link href={href}>
        <NavSpinner />
        {children}
      </Link>
    </Button>
  );
}
