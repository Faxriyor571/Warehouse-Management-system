import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { cn } from "@/lib/utils";
import { toastMutationError } from "@/lib/mutation";
import { useAuth } from "@/providers/auth-provider";
import { storeService } from "@/services/store";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { SkeletonCard } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

const storeFormSchema = z.object({
  name: z.string().min(2, "Nomi kamida 2 belgidan iborat bo'lishi kerak"),
  address: z.string().optional(),
});
type StoreFormValues = z.infer<typeof storeFormSchema>;

export default function StoresPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isCeo = user?.role === "ceo";
  const queryClient = useQueryClient();
  const [creating, setCreating] = React.useState(false);

  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list });

  const form = useForm<StoreFormValues>({
    resolver: zodResolver(storeFormSchema),
    defaultValues: { name: "", address: "" },
  });

  React.useEffect(() => {
    if (creating) form.reset({ name: "", address: "" });
  }, [creating, form]);

  const createMutation = useMutation({
    mutationFn: storeService.create,
    onSuccess: () => {
      toast.success("Do'kon yaratildi.");
      setCreating(false);
      void queryClient.invalidateQueries({ queryKey: ["stores"] });
    },
    onError: toastMutationError,
  });

  const stores = storesQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Do'konlar"
        description={isCeo ? "Do'konni tanlab batafsil ma'lumotni ko'ring." : "Kompaniyangizdagi do'konlar."}
        actions={
          isCeo ? (
            <Button onClick={() => setCreating(true)}>
              <Plus />
              Yangi do'kon
            </Button>
          ) : null
        }
      />

      <div className="mt-6">
        {storesQuery.isError ? (
          <ErrorState error={storesQuery.error} onRetry={() => void storesQuery.refetch()} />
        ) : storesQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : stores.length === 0 ? (
          <EmptyState
            title="Hozircha do'konlar yo'q"
            description={isCeo ? "Boshlash uchun birinchi do'koningizni yarating." : "Do'konlar topilmadi."}
            action={isCeo ? <Button size="sm" onClick={() => setCreating(true)}>Yangi do'kon</Button> : undefined}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {stores.map((store) => (
              <Card
                key={store.id}
                role={isCeo ? "button" : undefined}
                tabIndex={isCeo ? 0 : undefined}
                onClick={isCeo ? () => navigate(`/stores/${store.id}`) : undefined}
                onKeyDown={
                  isCeo
                    ? (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          navigate(`/stores/${store.id}`);
                        }
                      }
                    : undefined
                }
                className={cn(isCeo && "cursor-pointer transition-colors hover:border-primary/40")}
              >
                <CardContent className="flex items-center justify-between gap-3 p-5">
                  <p className="min-w-0 truncate text-base font-semibold text-foreground">{store.name}</p>
                  {store.is_active !== undefined ? (
                    <Badge variant={store.is_active ? "success" : "secondary"} dot>
                      {store.is_active ? "Faol" : "Nofaol"}
                    </Badge>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Modal
        open={creating}
        onOpenChange={setCreating}
        title="Yangi do'kon"
        footer={
          <>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit((v) => createMutation.mutate(v))} loading={createMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}>
          <FormField htmlFor="store-name" label="Nomi" required error={form.formState.errors.name?.message}>
            <Input id="store-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
          </FormField>
          <FormField htmlFor="store-address" label="Manzil">
            <Input id="store-address" {...form.register("address")} />
          </FormField>
        </form>
      </Modal>
    </ContentContainer>
  );
}
