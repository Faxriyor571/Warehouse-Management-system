import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { LogIn, Pencil, Plus, Power, PowerOff } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { getErrorMessage } from "@/lib/http";
import { formatDate } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { companyService } from "@/services/company";
import type { Company, CompanyStatus } from "@/types/company";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TableCard } from "@/components/ui/table-card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

const statusOptions = [
  { label: "Faol", value: "active" },
  { label: "Faolsizlantirilgan", value: "suspended" },
];

const companyFormSchema = z.object({
  name: z.string().min(2, "Nomi kamida 2 belgidan iborat bo'lishi kerak"),
  slug: z
    .string()
    .min(2, "Identifikator kamida 2 belgidan iborat bo'lishi kerak")
    .regex(/^[a-z0-9-]+$/, "Faqat kichik lotin harflari, raqamlar va chiziqcha"),
  contact_email: z.string().email("Email noto'g'ri").optional().or(z.literal("")),
  contact_phone: z.string().optional(),
  ceo_username: z.string().min(3, "Kamida 3 belgidan iborat bo'lishi kerak"),
  ceo_full_name: z.string().min(2, "Kamida 2 belgidan iborat bo'lishi kerak"),
  ceo_password: z.string().min(6, "Kamida 6 belgidan iborat bo'lishi kerak"),
  ceo_email: z.string().email("Email noto'g'ri").optional().or(z.literal("")),
});
type CompanyFormValues = z.infer<typeof companyFormSchema>;

const editFormSchema = z.object({
  name: z.string().min(2, "Nomi kamida 2 belgidan iborat bo'lishi kerak"),
  contact_email: z.string().email("Email noto'g'ri").optional().or(z.literal("")),
  contact_phone: z.string().optional(),
});
type EditFormValues = z.infer<typeof editFormSchema>;

export default function CompaniesPage() {
  const navigate = useNavigate();
  const { enterSupportSession } = useAuth();
  const queryClient = useQueryClient();

  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [editTarget, setEditTarget] = React.useState<Company | null>(null);
  const [suspendTarget, setSuspendTarget] = React.useState<Company | null>(null);
  const [enteringId, setEnteringId] = React.useState<number | null>(null);

  const companiesQuery = useQuery({
    queryKey: ["companies", { search, status }],
    queryFn: () => companyService.list({ search: search || undefined, status: (status || undefined) as CompanyStatus | undefined }),
  });

  const form = useForm<CompanyFormValues>({
    resolver: zodResolver(companyFormSchema),
    defaultValues: { name: "", slug: "", contact_email: "", contact_phone: "", ceo_username: "", ceo_full_name: "", ceo_password: "", ceo_email: "" },
  });

  const editForm = useForm<EditFormValues>({
    resolver: zodResolver(editFormSchema),
    defaultValues: { name: "", contact_email: "", contact_phone: "" },
  });

  React.useEffect(() => {
    if (editTarget) {
      editForm.reset({
        name: editTarget.name,
        contact_email: editTarget.contact_email ?? "",
        contact_phone: editTarget.contact_phone ?? "",
      });
    }
  }, [editTarget, editForm]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["companies"] });

  const createMutation = useMutation({
    mutationFn: (values: CompanyFormValues) =>
      companyService.create({
        name: values.name,
        slug: values.slug,
        contact_email: values.contact_email || null,
        contact_phone: values.contact_phone || null,
        ceo: {
          username: values.ceo_username,
          full_name: values.ceo_full_name,
          password: values.ceo_password,
          email: values.ceo_email || null,
        },
      }),
    onSuccess: (result) => {
      toast.success(`"${result.company.name}" kompaniyasi va uning CEO hisobi yaratildi.`);
      setIsCreateOpen(false);
      form.reset();
      void invalidate();
    },
    onError: toastMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: (values: EditFormValues) =>
      companyService.update(editTarget!.id, {
        name: values.name,
        contact_email: values.contact_email || null,
        contact_phone: values.contact_phone || null,
      }),
    onSuccess: () => {
      toast.success("Kompaniya yangilandi.");
      setEditTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const activateMutation = useMutation({
    mutationFn: companyService.activate,
    onSuccess: () => {
      toast.success("Kompaniya faollashtirildi.");
      void invalidate();
    },
    onError: toastMutationError,
  });

  const suspendMutation = useMutation({
    mutationFn: companyService.suspend,
    onSuccess: () => {
      toast.success("Kompaniya faolsizlantirildi.");
      setSuspendTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const onEnter = async (company: Company) => {
    setEnteringId(company.id);
    try {
      await enterSupportSession(company.id);
      navigate("/", { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setEnteringId(null);
    }
  };

  const companies = companiesQuery.data?.items ?? [];
  const activeCount = companies.filter((c) => c.status === "active").length;
  const suspendedCount = companies.filter((c) => c.status === "suspended").length;

  return (
    <ContentContainer>
      <PageHeader
        title="Kompaniyalar"
        description="Platformadagi barcha kompaniyalarni boshqaring — yarating, kirish huquqini nazorat qiling, kerak bo'lganda ularning nomidan kiring."
        actions={
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus />
            Yangi kompaniya
          </Button>
        }
      />

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Jami kompaniyalar</p>
          <p className="mt-1.5 text-2xl font-semibold tabular-nums">{companies.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Faol</p>
          <p className="mt-1.5 text-2xl font-semibold tabular-nums text-success">{activeCount}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Faolsizlantirilgan</p>
          <p className="mt-1.5 text-2xl font-semibold tabular-nums text-muted-foreground">{suspendedCount}</p>
        </Card>
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Input
            placeholder="Nomi bo'yicha qidirish…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
          <Select options={statusOptions} placeholder="Barcha holatlar" value={status} onChange={(e) => setStatus(e.target.value)} className="w-52" />
        </div>

        <TableCard>
          {companiesQuery.isError ? (
            <ErrorState error={companiesQuery.error} onRetry={() => void companiesQuery.refetch()} />
          ) : companiesQuery.isLoading ? (
            <TableSkeleton />
          ) : companies.length === 0 ? (
            <EmptyState
              title="Hozircha kompaniyalar yo'q"
              description="Boshlash uchun birinchi kompaniyani yarating."
              action={<Button size="sm" onClick={() => setIsCreateOpen(true)}>Yangi kompaniya</Button>}
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Nomi</TableHead>
                    <TableHead>Identifikator</TableHead>
                    <TableHead>Aloqa</TableHead>
                    <TableHead>Yaratilgan</TableHead>
                    <TableHead>Holati</TableHead>
                    <TableHead className="text-right" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {companies.map((company) => (
                    <TableRow key={company.id}>
                      <TableCell className="font-medium">{company.name}</TableCell>
                      <TableCell className="text-muted-foreground">{company.slug}</TableCell>
                      <TableCell className="text-muted-foreground">{company.contact_email ?? company.contact_phone ?? "—"}</TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(company.created_at)}</TableCell>
                      <TableCell>
                        <Badge variant={company.status === "active" ? "success" : "secondary"} dot>
                          {company.status === "active" ? "Faol" : "Faolsizlantirilgan"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={company.status !== "active"}
                            loading={enteringId === company.id}
                            onClick={() => void onEnter(company)}
                          >
                            <LogIn className="size-3.5" />
                            Kirish
                          </Button>
                          <Button variant="ghost" size="icon-sm" onClick={() => setEditTarget(company)} aria-label="Tahrirlash">
                            <Pencil className="size-4" />
                          </Button>
                          {company.status === "active" ? (
                            <Button variant="ghost" size="icon-sm" onClick={() => setSuspendTarget(company)} aria-label="Faolsizlantirish">
                              <PowerOff className="size-4" />
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              disabled={activateMutation.isPending}
                              onClick={() => activateMutation.mutate(company.id)}
                              aria-label="Faollashtirish"
                            >
                              <Power className="size-4 text-success" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </TableCard>
      </div>

      <Modal
        open={isCreateOpen}
        onOpenChange={(open) => !open && setIsCreateOpen(false)}
        title="Yangi kompaniya"
        description="Kompaniya va uning birinchi CEO hisobi birga yaratiladi."
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Bekor qilish
            </Button>
            <Button onClick={form.handleSubmit((v) => createMutation.mutate(v))} loading={createMutation.isPending}>
              Yaratish
            </Button>
          </>
        }
      >
        <form className="space-y-5" onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}>
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Kompaniya</p>
            <div className="grid grid-cols-2 gap-4">
              <FormField htmlFor="company-name" label="Nomi" required error={form.formState.errors.name?.message}>
                <Input id="company-name" invalid={!!form.formState.errors.name} {...form.register("name")} />
              </FormField>
              <FormField htmlFor="company-slug" label="Identifikator" required error={form.formState.errors.slug?.message}>
                <Input id="company-slug" placeholder="acme-agro" invalid={!!form.formState.errors.slug} {...form.register("slug")} />
              </FormField>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField htmlFor="company-email" label="Aloqa emaili" error={form.formState.errors.contact_email?.message}>
                <Input id="company-email" type="email" {...form.register("contact_email")} />
              </FormField>
              <FormField htmlFor="company-phone" label="Aloqa telefoni">
                <Input id="company-phone" placeholder="+998901234567" {...form.register("contact_phone")} />
              </FormField>
            </div>
          </div>

          <div className="space-y-3 border-t border-border/70 pt-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Birinchi CEO hisobi</p>
            <div className="grid grid-cols-2 gap-4">
              <FormField htmlFor="ceo-username" label="Username" required error={form.formState.errors.ceo_username?.message}>
                <Input id="ceo-username" invalid={!!form.formState.errors.ceo_username} {...form.register("ceo_username")} />
              </FormField>
              <FormField htmlFor="ceo-full-name" label="F.I.Sh." required error={form.formState.errors.ceo_full_name?.message}>
                <Input id="ceo-full-name" invalid={!!form.formState.errors.ceo_full_name} {...form.register("ceo_full_name")} />
              </FormField>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField htmlFor="ceo-password" label="Parol" required error={form.formState.errors.ceo_password?.message}>
                <Input id="ceo-password" type="password" invalid={!!form.formState.errors.ceo_password} {...form.register("ceo_password")} />
              </FormField>
              <FormField htmlFor="ceo-email" label="Email" error={form.formState.errors.ceo_email?.message}>
                <Input id="ceo-email" type="email" {...form.register("ceo_email")} />
              </FormField>
            </div>
          </div>
        </form>
      </Modal>

      <Modal
        open={editTarget !== null}
        onOpenChange={(open) => !open && setEditTarget(null)}
        title="Kompaniyani tahrirlash"
        description="Identifikator (slug) yaratilgandan keyin o'zgartirilmaydi."
        footer={
          <>
            <Button variant="outline" onClick={() => setEditTarget(null)}>
              Bekor qilish
            </Button>
            <Button onClick={editForm.handleSubmit((v) => updateMutation.mutate(v))} loading={updateMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={editForm.handleSubmit((v) => updateMutation.mutate(v))}>
          <FormField htmlFor="edit-company-name" label="Nomi" required error={editForm.formState.errors.name?.message}>
            <Input id="edit-company-name" invalid={!!editForm.formState.errors.name} {...editForm.register("name")} />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField htmlFor="edit-company-email" label="Aloqa emaili" error={editForm.formState.errors.contact_email?.message}>
              <Input id="edit-company-email" type="email" {...editForm.register("contact_email")} />
            </FormField>
            <FormField htmlFor="edit-company-phone" label="Aloqa telefoni">
              <Input id="edit-company-phone" placeholder="+998901234567" {...editForm.register("contact_phone")} />
            </FormField>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={suspendTarget !== null}
        onOpenChange={(open) => !open && setSuspendTarget(null)}
        title={`${suspendTarget?.name} faolsizlantirilsinmi?`}
        description="Kompaniyaning barcha faol seanslari yopiladi va uning foydalanuvchilari tizimga kira olmay qoladi."
        confirmLabel="Faolsizlantirish"
        variant="destructive"
        loading={suspendMutation.isPending}
        onConfirm={() => suspendTarget && suspendMutation.mutate(suspendTarget.id)}
      />
    </ContentContainer>
  );
}
