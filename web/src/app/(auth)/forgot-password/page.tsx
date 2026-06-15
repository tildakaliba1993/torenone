import Link from "next/link";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ForgotPasswordPage() {
  return (
    <Card>
      <CardHeader>
        <span className="font-mono text-xs tracking-widest text-accent uppercase">TorenOne</span>
        <CardTitle>Reset your password</CardTitle>
        <CardDescription>We’ll email you a secure link to set a new password.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <ForgotPasswordForm />
        <p className="text-sm text-muted">
          Remembered it?{" "}
          <Link className="text-accent hover:underline" href="/login">
            Back to sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
