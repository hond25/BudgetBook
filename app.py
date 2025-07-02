import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_NAME = "budget.db"

def init_db():
    conn = sqlite3. connect(DB_NAME)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = 1")
    c.execute("""
    CREATE TABLE IF NOT EXISTS item (
        item_code INTEGER PRIMARY KEY,
        item_name TEXT NOT NULL UNIQUE
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS acc_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acc_date TEXT NOT NULL,
        item_code INTEGER NOT NULL,
        amount INTEGER,
        FOREIGN KEY(item_code) REFERENCES item(item_code)
    )
    """)

    c.execute("INSERT OR IGNORE INTO item(item_code, item_name) VALUES (1, '食費'), (2, '交通費'), (3, '光熱費')")
    conn.commit()
    conn.close()

def get_items():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT item_code, item_name FROM item")
    items = c.fetchall()
    conn.close()
    return items

def add_record(date, item_code, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = 1")
    c.execute("INSERT INTO acc_data(acc_date, item_code, amount) VALUES (?, ?, ?)", (date, item_code, amount))
    conn.commit()
    conn.close()

def fetch_records():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    SELECT a.id, a.acc_date, i.item_name, a.amount
    FROM acc_data AS a
    JOIN item AS i ON a.item_code = i.item_code
    ORDER BY a.acc_date
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def fetch_total():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM acc_data")
    total = c.fetchone()[0]
    conn.close()
    return total if total else 0

class budgetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ぼくの家計簿アプリ")
        self.geometry("1000x600")
        self.create_widgets()
        self.refresh_table()

    def create_widgets(self):
        frame = ttk.Frame(self)
        frame.pack(pady=10)

        ttk.Label(frame, text="日付 (YYYY-MM-DD)").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(frame, textvariable=self.date_var)
        self.date_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.date_entry.bind("<KeyRelease>", self.on_date_entry)

        ttk.Label(frame, text="項目").grid(row=1, column=0, sticky=tk.W, pady=2)
        radio_frame = ttk.Frame(frame)
        radio_frame.grid(row=1, column=1, sticky=tk.W, pady=2)

        self.items = get_items()
        self.item_var = tk.StringVar(value=self.items[0][1])

        for code, name in self.items:
            ttk.Radiobutton(
                radio_frame,
                text=name,
                variable=self.item_var,
                value=name
            ).pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="金額").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.amount_entry = ttk.Entry(frame)
        self.amount_entry.grid(row=2, column=1, sticky=tk.W, pady=2)

        ttk.Button(frame, text="登録", command=self.on_add).grid(row=3, column=0, columnspan=2, pady=5)

        self.tree = ttk.Treeview(self, columns=("id", "data", "item", "amount"), show="headings")
        self.tree.heading("data", text="日付")
        self.tree.heading("item", text="項目")
        self.tree.heading("amount", text="金額")
        self.tree["displaycolumns"] = ("data", "item", "amount")
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # 合計ラベルと削除ボタンを横並びにするフレーム
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(pady=5)

        self.total_label = ttk.Label(bottom_frame, text="合計: 0 円")
        self.total_label.pack(side=tk.LEFT)

        self.delete_button = ttk.Button(bottom_frame, text="削除", command=self.on_delete)
        self.delete_button.pack(side=tk.LEFT, padx=10)

    def on_add(self):
        date = self.date_var.get()
        item_name = self.item_var.get()
        amount = self.amount_entry.get()

        if not date or not amount or not item_name:
            messagebox.showwarning("入力エラー", "すべtの項目を入力してください。")
            return
        try:
            amount = int(amount)
        except ValueError:
            messagebox.showwarning("入力エラー", "金額は整数で入力してください。")
            return
        item_code = [code for code, name in self.items if name == item_name][0]
        add_record(date, item_code, amount)
        self.refresh_table()
        self.date_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for rec in fetch_records():
            self.tree.insert("", tk.END, values=rec)
        self.total_label.config(text=f"合計: {fetch_total()} 円")

    def on_date_entry(self, event):
        value = self.date_var.get().replace("-", "")
        if len(value) > 8:
            value = value[:8]
        new_value = ""
        if len(value) >= 4:
            new_value += value[:4]  # 年
            if len(value) >= 6:
                new_value += "-" + value[4:6]  # 月
                if len(value) > 6:
                    new_value += "-" + value[6:8]  # 日
            elif len(value) > 4:
                new_value += "-" + value[4:]
        else:
            new_value += value
        self.date_var.set(new_value)

    def on_delete(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("選択エラー", "削除する行を選択してください。")
            return
        for item in selected:
            record_id = self.tree.item(item, "values")[0]  # idはvaluesの0番目
            self.delete_record(record_id)
        self.refresh_table()

    def delete_record(self, record_id):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM acc_data WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    init_db()
    app = budgetApp()
    app.mainloop()

    # test