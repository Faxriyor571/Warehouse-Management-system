import * as React from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { getErrorMessage } from "@/lib/http";
import { useAuth } from "@/providers/auth-provider";

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
    <main className="flex min-h-svh items-center justify-center bg-background px-6">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Tizimga kirish</h1>
          <p className="text-sm text-muted-foreground">
            Davom etish uchun ma'lumotlaringizni kiriting.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="space-y-2">
            <label htmlFor="username" className="text-sm font-medium">
              Foydalanuvchi nomi
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
              {...register("username")}
            />
            {errors.username ? (
              <p className="text-sm text-destructive">{errors.username.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              Parol
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
              {...register("password")}
            />
            {errors.password ? (
              <p className="text-sm text-destructive">{errors.password.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <label htmlFor="companySlug" className="text-sm font-medium">
              Kompaniya identifikatori
            </label>
            <input
              id="companySlug"
              type="text"
              autoComplete="organization"
              placeholder="Faqat CEO/sotuvchi uchun, adminlar bo'sh qoldirsin"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
              {...register("companySlug")}
            />
          </div>

          {submitError ? (
            <p className="text-sm text-destructive">{submitError}</p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {isSubmitting ? "Kirilmoqda…" : "Kirish"}
          </button>
        </form>
      </div>
    </main>
  );
}
