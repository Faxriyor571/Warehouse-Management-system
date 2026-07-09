import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { useAuth } from "@/providers/auth-provider";
import { settingService } from "@/services/setting";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

const settingFormSchema = z.object({
  key: z.string().min(1, "Kalit to'ldirilishi shart").max(100),
  value: z.string().optional(),
});
type SettingFormSchemaValues = z.infer<typeof settingFormSchema>;

type ModalState = "new" | { key: string; value: string | null } | null;

export default function SettingsPage() {
  const { user } = useAuth();
  // Settings has no separate read/manage tier — require_settings_manage
  // (CEO or the legacy admin) gates the whole page, so this only matters
  // for a non-CEO reaching the page directly by URL (the nav item is
  // already hidden for them) and seeing an action that could only 403.
  const canManage = user?.role === "ceo" || user?.role == null;
  const queryClient = useQueryClient();
  const [modalEntry, setModalEntry] = React.useState<ModalState>(null);

  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: settingService.get });

  const form = useForm<SettingFormSchemaValues>({
    resolver: zodResolver(settingFormSchema),
    defaultValues: { key: "", value: "" },
  });

  React.useEffect(() => {
    if (modalEntry && modalEntry !== "new") {
      form.reset({ key: modalEntry.key, value: modalEntry.value ?? "" });
    } else if (modalEntry === "new") {
      form.reset({ key: "", value: "" });
    }
  }, [modalEntry, form]);

  const upsertMutation = useMutation({
    mutationFn: (values: SettingFormSchemaValues) => settingService.upsert(values.key, values.value || null),
    onSuccess: () => {
      toast.success("Sozlama saqlandi.");
      setModalEntry(null);
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: toastMutationError,
  });

  const isEditingExisting = modalEntry !== null && modalEntry !== "new";
  const entries = Object.entries(settingsQuery.data ?? {});

  return (
    <ContentContainer>
      <PageHeader
        title="Sozlamalar"
        description="Kompaniyangizning konfiguratsiya kalit-qiymat juftliklari."
        actions={
          canManage ? (
            <Button onClick={() => setModalEntry("new")}>
              <Plus />
              Sozlama qo'shish
            </Button>
          ) : null
        }
      />

      <TableCard className="mt-6">
        {settingsQuery.isError ? (
          <ErrorState error={settingsQuery.error} onRetry={() => void settingsQuery.refetch()} />
        ) : settingsQuery.isLoading ? (
          <TableSkeleton />
        ) : entries.length === 0 ? (
          <EmptyState
            title="Hozircha sozlamalar yo'q"
            description={canManage ? "Boshlash uchun birinchi sozlamangizni qo'shing." : "Sozlamalar topilmadi."}
            action={canManage ? <Button size="sm" onClick={() => setModalEntry("new")}>Sozlama qo'shish</Button> : undefined}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Kalit</TableHead>
                <TableHead>Qiymat</TableHead>
                {canManage ? <TableHead className="text-right" /> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map(([key, value]) => (
                <TableRow key={key}>
                  <TableCell className="font-medium">{key}</TableCell>
                  <TableCell className="text-muted-foreground">{value ?? "—"}</TableCell>
                  {canManage ? (
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon-sm" onClick={() => setModalEntry({ key, value })} aria-label="Tahrirlash">
                        <Pencil className="size-4" />
                      </Button>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableCard>

      <Modal
        open={modalEntry !== null}
        onOpenChange={(open) => !open && setModalEntry(null)}
        title={modalEntry === "new" ? "Sozlama qo'shish" : "Sozlamani tahrirlash"}
        footer={
          <>
            <Button variant="outline" onClick={() => setModalEntry(null)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit((v) => upsertMutation.mutate(v))} loading={upsertMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={form.handleSubmit((v) => upsertMutation.mutate(v))}>
          <FormField htmlFor="setting-key" label="Kalit" required error={form.formState.errors.key?.message}>
            <Input id="setting-key" disabled={isEditingExisting} invalid={!!form.formState.errors.key} {...form.register("key")} />
          </FormField>
          <FormField htmlFor="setting-value" label="Qiymat">
            <Input id="setting-value" {...form.register("value")} />
          </FormField>
        </form>
      </Modal>
    </ContentContainer>
  );
}
