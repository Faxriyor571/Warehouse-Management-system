export interface Unit {
  id: number;
  name: string;
  short_name: string;
  conversion_factor: string | null;
  is_active: boolean;
}
