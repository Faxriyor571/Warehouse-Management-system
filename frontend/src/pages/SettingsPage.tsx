import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { useAuth } from "@/providers/auth-provider";
import { settingService } from "@/services/setting";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/feedback/error-state";
import { EmptyState } from "@/components/feedback/empty-state";
import { FormField } from "@/components/forms/form-field";

const companyNameFormSchema = z.object({
  name: z.string().min(2, "Nomi kamida 2 belgidan iborat bo'lishi kerak"),
});
type CompanyNameFormValues = z.infer<typeof companyNameFormSchema>;

export default function SettingsPage() {
  const { user } = useAuth();
  // The legacy single-tenant admin (role === null) has no Company row at
  // all — settings/company structurally 422s for it. Short-circuit with a
  // clear message instead of firing the query and rendering that as a
  // generic, uselessly-retryable error.
  const hasCompany = user?.company_id != null;
  const queryClient = useQueryClient();
  const companyQuery = useQuery({
    queryKey: ["settings", "company"],
    queryFn: settingService.getCompany,
    enabled: hasCompany,
  });

  const form = useForm<CompanyNameFormValues>({
    resolver: zodResolver(companyNameFormSchema),
    defaultValues: { name: "" },
  });

  React.useEffect(() => {
    if (companyQuery.data) form.reset({ name: companyQuery.data.name });
  }, [companyQuery.data, form]);

  const updateMutation = useMutation({
    mutationFn: (values: CompanyNameFormValues) => settingService.updateCompany(values.name),
    onSuccess: () => {
      toast.success("Kompaniya nomi yangilandi.");
      void queryClient.invalidateQueries({ queryKey: ["settings", "company"] });
    },
    onError: toastMutationError,
  });

  return (
    <ContentContainer>
      <PageHeader title="Sozlamalar" description="Kompaniyangiz profilini boshqaring." />

      <Card className="mt-6 max-w-lg">
        <CardContent className="p-5">
          {!hasCompany ? (
            <EmptyState compact title="Kompaniya profili mavjud emas" description="Bu funksiya yagona tenant (legacy admin) rejimida mavjud emas." />
          ) : companyQuery.isError ? (
            <ErrorState error={companyQuery.error} onRetry={() => void companyQuery.refetch()} />
          ) : companyQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <form className="space-y-4" onSubmit={form.handleSubmit((v) => updateMutation.mutate(v))}>
              <FormField htmlFor="company-name" label="Kompaniya nomi" required error={form.formState.errors.name?.message}>
                <Input id="company-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
              </FormField>
              <div className="flex justify-end">
                <Button type="submit" loading={updateMutation.isPending}>
                  Saqlash
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </ContentContainer>
  );
}
