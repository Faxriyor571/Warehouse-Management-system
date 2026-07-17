export interface Employee {
  id: number;
  username: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  role: string;
  store_id: number;
  store_name: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface EmployeeCreateFormValues {
  username: string;
  full_name: string;
  password: string;
  store_id: string;
}

export interface EmployeeUpdateFormValues {
  full_name: string;
  store_id: string;
}

export interface EmployeePasswordResetFormValues {
  new_password: string;
}
