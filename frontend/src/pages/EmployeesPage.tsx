import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { KeyRound, Pencil, Plus, Power } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { toastMutationError } from "@/lib/mutation";
import { formatDateTime } from "@/lib/formatters";
import { useAuth } from "@/providers/auth-provider";
import { employeeService } from "@/services/employee";
import { storeService } from "@/services/store";
import type { Employee } from "@/types/employee";
import { ContentContainer } from "@/components/layout/content-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { SkeletonCard } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { FormField } from "@/components/forms/form-field";

const createFormSchema = z.object({
  username: z.string().min(3, "Kamida 3 belgidan iborat bo'lishi kerak"),
  full_name: z.string().min(2, "Kamida 2 belgidan iborat bo'lishi kerak"),
  password: z.string().min(6, "Kamida 6 belgidan iborat bo'lishi kerak"),
  store_id: z.string().min(1, "Do'konni tanlash shart"),
});
type CreateFormValues = z.infer<typeof createFormSchema>;

const updateFormSchema = z.object({
  full_name: z.string().min(2, "Kamida 2 belgidan iborat bo'lishi kerak"),
  store_id: z.string().min(1, "Do'konni tanlash shart"),
});
type UpdateFormValues = z.infer<typeof updateFormSchema>;

const passwordFormSchema = z.object({
  new_password: z.string().min(6, "Kamida 6 belgidan iborat bo'lishi kerak"),
});
type PasswordFormValues = z.infer<typeof passwordFormSchema>;

type ModalState = "new" | Employee | null;

export default function EmployeesPage() {
  const { user } = useAuth();
  // Employees is CEO-only on the backend (RequireCEO has no legacy-admin
  // branch, see app/routers/employees.py) — this page is only reachable via
  // direct URL for anyone else, since navigation.ts already hides the nav
  // item. Gate the create action to match, same pattern as StoresPage.
  const isCeo = user?.role === "ceo";
  const queryClient = useQueryClient();
  const [modalEmployee, setModalEmployee] = React.useState<ModalState>(null);
  const [passwordTarget, setPasswordTarget] = React.useState<Employee | null>(null);
  const [deactivateTarget, setDeactivateTarget] = React.useState<Employee | null>(null);

  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: () => employeeService.list() });
  const storesQuery = useQuery({ queryKey: ["stores"], queryFn: storeService.list });

  const storeOptions = React.useMemo(
    () => (storesQuery.data ?? []).map((s) => ({ label: s.name, value: String(s.id) })),
    [storesQuery.data]
  );

  const createForm = useForm<CreateFormValues>({
    resolver: zodResolver(createFormSchema),
    defaultValues: { username: "", full_name: "", password: "", store_id: "" },
  });

  const updateForm = useForm<UpdateFormValues>({
    resolver: zodResolver(updateFormSchema),
    defaultValues: { full_name: "", store_id: "" },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordFormSchema),
    defaultValues: { new_password: "" },
  });

  React.useEffect(() => {
    if (modalEmployee === "new") {
      createForm.reset({ username: "", full_name: "", password: "", store_id: "" });
    } else if (modalEmployee) {
      updateForm.reset({ full_name: modalEmployee.full_name, store_id: String(modalEmployee.store_id) });
    }
  }, [modalEmployee, createForm, updateForm]);

  React.useEffect(() => {
    if (passwordTarget) {
      passwordForm.reset({ new_password: "" });
    }
  }, [passwordTarget, passwordForm]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["employees"] });

  const createMutation = useMutation({
    mutationFn: employeeService.create,
    onSuccess: () => {
      toast.success("Sotuvchi qo'shildi.");
      setModalEmployee(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: UpdateFormValues }) => employeeService.update(id, values),
    onSuccess: () => {
      toast.success("Sotuvchi yangilandi.");
      setModalEmployee(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const activateMutation = useMutation({
    mutationFn: employeeService.activate,
    onSuccess: () => {
      toast.success("Sotuvchi faollashtirildi.");
      void invalidate();
    },
    onError: toastMutationError,
  });

  const deactivateMutation = useMutation({
    mutationFn: employeeService.deactivate,
    onSuccess: () => {
      toast.success("Sotuvchi nofaol qilindi.");
      setDeactivateTarget(null);
      void invalidate();
    },
    onError: toastMutationError,
  });

  const passwordMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: PasswordFormValues }) => employeeService.resetPassword(id, values),
    onSuccess: () => {
      toast.success("Parol tiklandi.");
      setPasswordTarget(null);
    },
    onError: toastMutationError,
  });

  const employees = employeesQuery.data ?? [];

  return (
    <ContentContainer>
      <PageHeader
        title="Sotuvchilar"
        description="Kompaniyangiz do'konlaridagi sotuvchi xodimlarni boshqaring."
        actions={
          isCeo ? (
            <Button onClick={() => setModalEmployee("new")}>
              <Plus />
              Yangi sotuvchi
            </Button>
          ) : null
        }
      />

      <div className="mt-6">
        {employeesQuery.isError ? (
          <ErrorState error={employeesQuery.error} onRetry={() => void employeesQuery.refetch()} />
        ) : employeesQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : employees.length === 0 ? (
          <EmptyState
            title="Hozircha sotuvchilar yo'q"
            description="Boshlash uchun birinchi sotuvchingizni qo'shing."
            action={isCeo ? <Button size="sm" onClick={() => setModalEmployee("new")}>Yangi sotuvchi</Button> : undefined}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {employees.map((employee) => (
              <Card key={employee.id}>
                <CardContent className="space-y-3 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-base font-semibold text-foreground">{employee.full_name}</p>
                      <p className="truncate text-sm text-muted-foreground">@{employee.username}</p>
                    </div>
                    <Badge variant={employee.is_active ? "success" : "secondary"} dot>
                      {employee.is_active ? "Faol" : "Nofaol"}
                    </Badge>
                  </div>
                  <dl className="space-y-1 text-sm">
                    <div className="flex justify-between gap-2">
                      <dt className="text-muted-foreground">Do'kon</dt>
                      <dd className="truncate font-medium text-foreground">{employee.store_name}</dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="text-muted-foreground">Oxirgi kirish</dt>
                      <dd className="text-foreground">{employee.last_login_at ? formatDateTime(employee.last_login_at) : "—"}</dd>
                    </div>
                  </dl>
                  {isCeo ? (
                    <div className="flex justify-end gap-1.5 border-t border-border/70 pt-3">
                      <Button variant="ghost" size="icon-sm" onClick={() => setModalEmployee(employee)} aria-label="Tahrirlash">
                        <Pencil className="size-4" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => setPasswordTarget(employee)} aria-label="Parolni tiklash">
                        <KeyRound className="size-4" />
                      </Button>
                      {employee.is_active ? (
                        <Button variant="ghost" size="icon-sm" onClick={() => setDeactivateTarget(employee)} aria-label="Nofaol qilish">
                          <Power className="size-4" />
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          disabled={activateMutation.isPending}
                          onClick={() => activateMutation.mutate(employee.id)}
                          aria-label="Faollashtirish"
                        >
                          <Power className="size-4 text-success" />
                        </Button>
                      )}
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Modal
        open={modalEmployee === "new"}
        onOpenChange={(open) => !open && setModalEmployee(null)}
        title="Yangi sotuvchi"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setModalEmployee(null)}>
              Bekor qilish
            </Button>
            <Button onClick={createForm.handleSubmit((v) => createMutation.mutate(v))} loading={createMutation.isPending}>
              Saqlash
            </Button>
          </>
        }
      >
        <form className="space-y-4" onSubmit={createForm.handleSubmit((v) => createMutation.mutate(v))}>
          <div className="grid grid-cols-2 gap-4">
            <FormField htmlFor="employee-username" label="Username" required error={createForm.formState.errors.username?.message}>
              <Input id="employee-username" invalid={!!createForm.formState.errors.username} {...createForm.register("username")} />
            </FormField>
            <FormField htmlFor="employee-full-name" label="F.I.Sh." required error={createForm.formState.errors.full_name?.message}>
              <Input id="employee-full-name" invalid={!!createForm.formState.errors.full_name} {...createForm.register("full_name")} />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField htmlFor="employee-password" label="Parol" required error={createForm.formState.errors.password?.message}>
              <Input id="employee-password" type="password" invalid={!!createForm.formState.errors.password} {...createForm.register("password")} />
            </FormField>
            <FormField htmlFor="employee-store" label="Do'kon" required error={createForm.formState.errors.store_id?.message}>
              <Select
                id="employee-store"
                options={storeOptions}
                placeholder="Do'konni tanlang…"
                invalid={!!createForm.formState.errors.store_id}
                {...createForm.register("store_id")}
              />
            </FormField>
          </div>
        </form>
      </Modal>

      <Modal
        open={modalEmployee !== null && modalEmployee !== "new"}
        onOpenChange={(open) => !open && setModalEmployee(null)}
        title="Sotuvchini tahrirlash"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setModalEmployee(null)}>
              Bekor qilish
            </Button>
            <Button
              onClick={updateForm.handleSubmit((v) => modalEmployee && modalEmployee !== "new" && updateMutation.mutate({ id: modalEmployee.id, values: v }))}
              loading={updateMutation.isPending}
            >
              Saqlash
            </Button>
          </>
        }
      >
        <form
          className="space-y-4"
          onSubmit={updateForm.handleSubmit((v) => modalEmployee && modalEmployee !== "new" && updateMutation.mutate({ id: modalEmployee.id, values: v }))}
        >
          <FormField htmlFor="employee-edit-full-name" label="F.I.Sh." required error={updateForm.formState.errors.full_name?.message}>
            <Input id="employee-edit-full-name" invalid={!!updateForm.formState.errors.full_name} {...updateForm.register("full_name")} />
          </FormField>
          <FormField htmlFor="employee-edit-store" label="Do'kon" required error={updateForm.formState.errors.store_id?.message}>
            <Select
              id="employee-edit-store"
              options={storeOptions}
              invalid={!!updateForm.formState.errors.store_id}
              {...updateForm.register("store_id")}
            />
          </FormField>
        </form>
      </Modal>

      <Modal
        open={passwordTarget !== null}
        onOpenChange={(open) => !open && setPasswordTarget(null)}
        title={`${passwordTarget?.full_name} paroli`}
        description="Yangi parolni kiriting va sotuvchiga xabar bering."
        footer={
          <>
            <Button variant="outline" onClick={() => setPasswordTarget(null)}>
              Bekor qilish
            </Button>
            <Button
              onClick={passwordForm.handleSubmit((v) => passwordTarget && passwordMutation.mutate({ id: passwordTarget.id, values: v }))}
              loading={passwordMutation.isPending}
            >
              Tiklash
            </Button>
          </>
        }
      >
        <form
          className="space-y-4"
          onSubmit={passwordForm.handleSubmit((v) => passwordTarget && passwordMutation.mutate({ id: passwordTarget.id, values: v }))}
        >
          <FormField htmlFor="employee-new-password" label="Yangi parol" required error={passwordForm.formState.errors.new_password?.message}>
            <Input id="employee-new-password" type="password" invalid={!!passwordForm.formState.errors.new_password} {...passwordForm.register("new_password")} />
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        open={deactivateTarget !== null}
        onOpenChange={(open) => !open && setDeactivateTarget(null)}
        title={`${deactivateTarget?.full_name} nofaol qilinsinmi?`}
        description="Nofaol sotuvchi tizimga kira olmaydi."
        confirmLabel="Nofaol qilish"
        variant="destructive"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)}
      />
    </ContentContainer>
  );
}
