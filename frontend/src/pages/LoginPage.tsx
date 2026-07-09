import * as React from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { AlertCircle, Warehouse } from "lucide-react";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { FormField } from "@/components/forms/form-field";

const schema = z.object({
  username: z.string().min(1, "Foydalanuvchi nomi to'ldirilishi shart"),
  password: z.string().min(1, "Parol to'ldirilishi shart"),
  companySlug: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, login } = useAuth();
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (values: FormValues) => {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await login(values.username, values.password, values.companySlug || undefined);
      navigate("/", { replace: true });
    } catch (error) {
      setSubmitError(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="relative flex min-h-svh items-center justify-center overflow-hidden bg-background px-6">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_0%,hsl(var(--primary)/0.10),transparent)]"
      />

      <div className="relative w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <span className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-sm ring-1 ring-primary/20">
            <Warehouse className="size-[22px]" strokeWidth={2.25} />
          </span>
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight text-foreground">Ombor Boshqaruv Tizimi</h1>
            <p className="text-sm text-muted-foreground">Davom etish uchun ma'lumotlaringizni kiriting.</p>
          </div>
        </div>

        <Card>
          <CardContent className="p-6">
            <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
              <FormField htmlFor="username" label="Foydalanuvchi nomi" required error={errors.username?.message}>
                <Input
                  id="username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  invalid={!!errors.username}
                  {...register("username")}
                />
              </FormField>

              <FormField htmlFor="password" label="Parol" required error={errors.password?.message}>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  invalid={!!errors.password}
                  {...register("password")}
                />
              </FormField>

              <FormField
                htmlFor="companySlug"
                label="Kompaniya identifikatori"
                description="Faqat CEO yoki sotuvchi uchun — administratorlar bo'sh qoldirsin."
              >
                <Input id="companySlug" type="text" autoComplete="organization" placeholder="masalan: acme-agro" {...register("companySlug")} />
              </FormField>

              {submitError ? (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
                  <AlertCircle className="mt-0.5 size-4 shrink-0" strokeWidth={2.25} />
                  <p>{submitError}</p>
                </div>
              ) : null}

              <Button type="submit" className="w-full" loading={isSubmitting}>
                Kirish
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
