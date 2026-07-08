import { http } from "@/lib/http";
import type { PaginatedResponse } from "@/types/common";
import type {
  Employee,
  EmployeeCreateFormValues,
  EmployeePasswordResetFormValues,
  EmployeeUpdateFormValues,
} from "@/types/employee";

export const employeeService = {
  async list(search?: string): Promise<Employee[]> {
    const { data } = await http.get<PaginatedResponse<Employee>>("/employees", {
      params: { page_size: 200, ...(search ? { search } : {}) },
    });
    return data.items;
  },

  async create(values: EmployeeCreateFormValues): Promise<Employee> {
    const { data } = await http.post<Employee>("/employees", {
      username: values.username,
      full_name: values.full_name,
      password: values.password,
      email: values.email || null,
      phone: values.phone || null,
      store_id: Number(values.store_id),
    });
    return data;
  },

  async update(id: number, values: EmployeeUpdateFormValues): Promise<Employee> {
    const { data } = await http.put<Employee>(`/employees/${id}`, {
      full_name: values.full_name,
      email: values.email || null,
      phone: values.phone || null,
      store_id: Number(values.store_id),
    });
    return data;
  },

  async activate(id: number): Promise<Employee> {
    const { data } = await http.post<Employee>(`/employees/${id}/activate`);
    return data;
  },

  async deactivate(id: number): Promise<Employee> {
    const { data } = await http.post<Employee>(`/employees/${id}/deactivate`);
    return data;
  },

  async resetPassword(id: number, values: EmployeePasswordResetFormValues): Promise<void> {
    await http.post(`/employees/${id}/reset-password`, { new_password: values.new_password });
  },
};
