import sqlite3
import csv
from datetime import datetime


class UtilityService:
    def __init__(self, db_name="utilities.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    # ----------------- БАЗА ДАННЫХ -----------------

    def create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS meters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            meter_type TEXT,
            last_value REAL,
            FOREIGN KEY(tenant_id) REFERENCES tenants(id)
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meter_id INTEGER,
            date TEXT,
            old_value REAL,
            new_value REAL,
            usage REAL,
            cost REAL,
            FOREIGN KEY(meter_id) REFERENCES meters(id)
        )
        """)

        self.conn.commit()

    # ----------------- ЖИЛЬЦЫ -----------------

    def add_tenant(self, name):
        self.cursor.execute("INSERT INTO tenants (name) VALUES (?)", (name,))
        self.conn.commit()

    def get_tenants(self):
        self.cursor.execute("SELECT * FROM tenants")
        return self.cursor.fetchall()

    # ----------------- СЧЁТЧИКИ -----------------

    def add_meter(self, tenant_id, meter_type, initial_value):
        self.cursor.execute("""
        INSERT INTO meters (tenant_id, meter_type, last_value)
        VALUES (?, ?, ?)
        """, (tenant_id, meter_type, initial_value))
        self.conn.commit()

    def get_meters(self):
        self.cursor.execute("""
        SELECT meters.id, tenants.name, meters.meter_type, meters.last_value
        FROM meters
        JOIN tenants ON meters.tenant_id = tenants.id
        """)
        return self.cursor.fetchall()

    # ----------------- ПОКАЗАНИЯ -----------------

    TARIFFS = {
        "electricity": 6.2,
        "water": 42.0,
        "gas": 8.1
    }

    def add_meter_reading(self, meter_id, new_value):
        self.cursor.execute("SELECT last_value, meter_type FROM meters WHERE id=?", (meter_id,))
        row = self.cursor.fetchone()

        if not row:
            raise ValueError("Счётчик не найден")

        old_value, meter_type = row
        usage = new_value - old_value
        cost = usage * self.TARIFFS.get(meter_type, 1)

        # Сохраняем запись
        self.cursor.execute("""
        INSERT INTO payments (meter_id, date, old_value, new_value, usage, cost)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (meter_id, datetime.now().date(), old_value, new_value, usage, cost))

        # Обновляем счётчик
        self.cursor.execute("UPDATE meters SET last_value=? WHERE id=?", (new_value, meter_id))
        self.conn.commit()

        return usage, cost

    def get_payments(self):
        self.cursor.execute("""
        SELECT payments.id, tenants.name, meters.meter_type,
               payments.date, payments.usage, payments.cost
        FROM payments
        JOIN meters ON payments.meter_id = meters.id
        JOIN tenants ON meters.tenant_id = tenants.id
        ORDER BY payments.date DESC
        """)
        return self.cursor.fetchall()

    # ----------------- ЭКСПОРТ -----------------

    def export_payments_csv(self, filename="payments.csv"):
        rows = self.get_payments()
        with open(filename, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Жилец", "Тип счётчика", "Дата", "Расход", "Стоимость"])
            writer.writerows(rows)
        return filename


# ----------------- КОНСОЛЬНОЕ МЕНЮ -----------------

def main():
    service = UtilityService()

    while True:
        print("\n--- УЧЁТ КОММУНАЛЬНЫХ ПЛАТЕЖЕЙ ---")
        print("1. Добавить жильца")
        print("2. Добавить счётчик")
        print("3. Ввести показания")
        print("4. Показать все платежи")
        print("5. Экспорт в CSV")
        print("0. Выход")

        choice = input("Выберите действие: ")

        if choice == "1":
            name = input("Имя жильца: ")
            service.add_tenant(name)
            print("Жилец добавлен.")

        elif choice == "2":
            tenants = service.get_tenants()
            print("\nЖильцы:")
            for t in tenants:
                print(f"{t[0]} — {t[1]}")

            tenant_id = int(input("ID жильца: "))
            meter_type = input("Тип счётчика (electricity/water/gas): ")
            initial = float(input("Начальные показания: "))

            service.add_meter(tenant_id, meter_type, initial)
            print("Счётчик добавлен.")

        elif choice == "3":
            meters = service.get_meters()
            print("\nСчётчики:")
            for m in meters:
                print(f"{m[0]} — {m[1]}, {m[2]}, текущее {m[3]}")

            meter_id = int(input("ID счётчика: "))
            new_value = float(input("Новые показания: "))

            usage, cost = service.add_meter_reading(meter_id, new_value)
            print(f"Расход: {usage}, Стоимость: {cost} руб.")

        elif choice == "4":
            payments = service.get_payments()
            for p in payments:
                print(p)

        elif choice == "5":
            file = service.export_payments_csv()
            print("Экспорт выполнен:", file)

        elif choice == "0":
            break

        else:
            print("Неверный ввод!")


if __name__ == "__main__":
    main()
