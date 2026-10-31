import time
import tkinter as tk
from tkinter import ttk, messagebox

CROSS = [(-1, 0), (1, 0), (0, -1), (0, 1)]    
DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  
OPERATORS = {
    "cross": ("Вверх-вниз-вправо-вліво", CROSS),
    "diag": ("По діагоналях", DIAG),
    "combined": ("Комбінований (хрест + діагоналі)", CROSS + DIAG),
}

def make_maze(rows, cols, density_percent, seed, start, target):
    state = (seed * 2654435761 + 12345) % (2 ** 32)
    grid = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            state = (1103515245 * state + 12345) % (2 ** 31)
            if (state >> 8) % 100 < density_percent:
                grid[r][c] = -1
    grid[start[0]][start[1]] = 0
    grid[target[0]][target[1]] = 0
    return grid

def wave_search(grid, start, target, operator_key):
    ops = OPERATORS[operator_key][1]
    rows, cols = len(grid), len(grid[0])
    wave = [[-1 if grid[r][c] == -1 else 0 for c in range(cols)] for r in range(rows)]
    t0 = time.perf_counter()
    wave[start[0]][start[1]] = 1
    front = [start]
    fronts = [[start]]
    cycles = 0
    expanded = 0
    found = (start == target)
    while front and not found:
        cycles += 1
        new_front = []
        for (r, c) in front:
            expanded += 1
            for dr, dc in ops:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and wave[nr][nc] == 0:
                    wave[nr][nc] = wave[r][c] + 1
                    new_front.append((nr, nc))
                    if (nr, nc) == target:
                        found = True
            if found:
                break
        if new_front:
            fronts.append(new_front)
        front = new_front
    path = []
    if found:
        cur = target
        path = [cur]
        while cur != start:
            r, c = cur
            for dr, dc in ops:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and wave[nr][nc] == wave[r][c] - 1 and wave[nr][nc] > 0:
                    cur = (nr, nc)
                    break
            path.append(cur)
        path.reverse()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    marked = sum(1 for r in range(rows) for c in range(cols) if wave[r][c] > 0)
    return {"found": found, "path": path, "wave": wave, "fronts": fronts,
            "cycles": cycles, "expanded": expanded, "marked": marked,
            "time_ms": elapsed_ms}

C_FREE, C_WALL = "#ffffff", "#2c3e50"
C_START, C_TARGET, C_PATH = "#2e86de", "#c0392b", "#27ae60"
EDIT_MODES = {
    "view": "Перегляд (без редагування)",
    "wall": "Стіни: клік / протягування (додати-прибрати)",
    "start": "Задати початкову вершину (клік)",
    "target": "Задати цільову вершину (клік)",
}


def wave_color(k, kmax):
    t = 0 if kmax <= 1 else min(1.0, (k - 1) / (kmax - 1))
    r = int(255 - 40 * t)
    g = int(240 - 120 * t)
    b = int(150 - 60 * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class WaveApp:
    def __init__(self, root):
        self.root = root
        root.title("Лаб. №3 — Одно-направлений хвильовий пошук у лабіринті")
        root.geometry("1360x900")
        self.rows = self.cols = 15
        self.start, self.target = (0, 0), (14, 14)
        self.grid = make_maze(15, 15, 20, 1, self.start, self.target)
        self.wave = None
        self.path = set()
        self.cell = 40
        self.animating = False
        self.job = None
        self.paint_value = None
        self._build()
        self._redraw()

    def _build(self):
        main = ttk.Frame(self.root); main.pack(fill="both", expand=True)
        panel = ttk.Frame(main, padding=10); panel.pack(side="left", fill="y")
        ttk.Label(panel, text="Керування пошуком", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))

        ttk.Label(panel, text="Розмір лабіринту (рядків × стовпців)").pack(anchor="w")
        sf = ttk.Frame(panel); sf.pack(anchor="w", pady=(0, 6))
        self.rows_var, self.cols_var = tk.IntVar(value=15), tk.IntVar(value=15)
        ttk.Spinbox(sf, from_=10, to=30, width=5, textvariable=self.rows_var).pack(side="left")
        ttk.Label(sf, text=" × ").pack(side="left")
        ttk.Spinbox(sf, from_=10, to=30, width=5, textvariable=self.cols_var).pack(side="left")

        ttk.Label(panel, text="Щільність непрохідних клітинок, %").pack(anchor="w")
        self.density_var = tk.IntVar(value=20)
        ttk.Spinbox(panel, from_=0, to=60, width=6, textvariable=self.density_var).pack(anchor="w", pady=(0, 6))
        ttk.Label(panel, text="Seed (номер варіанта лабіринту)").pack(anchor="w")
        self.seed_var = tk.IntVar(value=1)
        ttk.Spinbox(panel, from_=0, to=9999, width=6, textvariable=self.seed_var).pack(anchor="w", pady=(0, 6))
        ttk.Button(panel, text="Побудувати лабіринт", command=self.generate).pack(fill="x", pady=2)
        ttk.Button(panel, text="Очистити всі стіни", command=self.clear_walls).pack(fill="x", pady=2)

        ttk.Label(panel, text="Оператор переходу").pack(anchor="w", pady=(8, 0))
        self.op_combo = ttk.Combobox(panel, state="readonly", width=34, values=[v[0] for v in OPERATORS.values()])
        self.op_combo.set(OPERATORS["cross"][0]); self.op_combo.pack(anchor="w", pady=(0, 6))

        ttk.Label(panel, text="Затримка між циклами хвилі, мс").pack(anchor="w")
        self.delay_var = tk.IntVar(value=150)
        ttk.Scale(panel, from_=1000, to=0, orient="horizontal", variable=self.delay_var).pack(fill="x")
        self.instant = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text="Миттєво (без анімації)", variable=self.instant).pack(anchor="w")
        self.show_nums = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="Показувати значення матриці (-1, 0, мітки хвилі)",
                        variable=self.show_nums, command=self._redraw).pack(anchor="w", pady=(0, 6))

        ttk.Button(panel, text="▶ Запустити хвильовий пошук", command=self.run).pack(fill="x", pady=2)
        ttk.Button(panel, text="⏹ Зупинити анімацію", command=self.stop).pack(fill="x", pady=2)
        ttk.Button(panel, text="Порівняти оператори переходу", command=self.compare).pack(fill="x", pady=2)

        box = ttk.LabelFrame(panel, text="Ручне редагування лабіринту", padding=6)
        box.pack(fill="x", pady=8)
        self.edit_combo = ttk.Combobox(box, state="readonly", width=34, values=list(EDIT_MODES.values()))
        self.edit_combo.set(EDIT_MODES["view"]); self.edit_combo.pack(fill="x")
        self.status = tk.StringVar(value="Готово.")
        ttk.Label(panel, textvariable=self.status, wraplength=290, foreground="#333").pack(anchor="w")

        leg = ttk.LabelFrame(panel, text="Умовні позначення", padding=6); leg.pack(fill="x", pady=8)
        for col, txt in [(C_START, "початкова вершина"), (C_TARGET, "цільова вершина"),
                         (C_WALL, "непрохідна клітинка (-1)"), (C_FREE, "прохідна клітинка (0)"),
                         ("#f5d76e", "клітинка хвилі (мітка = відстань + 1)"), (C_PATH, "знайдений шлях")]:
            row = ttk.Frame(leg); row.pack(anchor="w")
            sw = tk.Canvas(row, width=14, height=14, highlightthickness=0)
            sw.create_rectangle(1, 1, 13, 13, fill=col, outline="#888"); sw.pack(side="left", padx=4)
            ttk.Label(row, text=txt).pack(side="left")

        self.canvas = tk.Canvas(main, bg="white", width=1000, height=880)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "paint_value", None))

    def op_key(self):
        for k, v in OPERATORS.items():
            if v[0] == self.op_combo.get():
                return k
        return "cross"

    def edit_key(self):
        for k, v in EDIT_MODES.items():
            if v == self.edit_combo.get():
                return k
        return "view"

    def generate(self):
        self.stop()
        self.rows, self.cols = int(self.rows_var.get()), int(self.cols_var.get())
        self.start, self.target = (0, 0), (self.rows - 1, self.cols - 1)
        self.grid = make_maze(self.rows, self.cols, int(self.density_var.get()), int(self.seed_var.get()),
                              self.start, self.target)
        self.wave, self.path = None, set()
        walls = sum(row.count(-1) for row in self.grid)
        self.status.set(f"Лабіринт {self.rows}×{self.cols}, стін: {walls} ({100*walls/(self.rows*self.cols):.1f}%).")
        self._redraw()

    def clear_walls(self):
        self.stop()
        self.grid = [[0] * self.cols for _ in range(self.rows)]
        self.wave, self.path = None, set()
        self.status.set("Усі стіни вилучено."); self._redraw()

    def _cell_at(self, x, y):
        c, r = int((x - self.ox) // self.cell), int((y - self.oy) // self.cell)
        return (r, c) if 0 <= r < self.rows and 0 <= c < self.cols else None

    def _press(self, e):
        cell = self._cell_at(e.x, e.y); mode = self.edit_key()
        if cell is None or mode == "view":
            return
        r, c = cell
        if mode == "wall":
            if cell in (self.start, self.target):
                return
            self.paint_value = 0 if self.grid[r][c] == -1 else -1
            self._paint(cell)
        elif mode == "start" and self.grid[r][c] != -1 and cell != self.target:
            self.start = cell; self.wave, self.path = None, set()
            self.status.set(f"Початкову вершину задано: ({r+1}, {c+1})."); self._redraw()
        elif mode == "target" and self.grid[r][c] != -1 and cell != self.start:
            self.target = cell; self.wave, self.path = None, set()
            self.status.set(f"Цільову вершину задано: ({r+1}, {c+1})."); self._redraw()

    def _drag(self, e):
        if self.edit_key() == "wall" and self.paint_value is not None:
            cell = self._cell_at(e.x, e.y)
            if cell and cell not in (self.start, self.target):
                self._paint(cell)

    def _paint(self, cell):
        r, c = cell
        if self.grid[r][c] != self.paint_value:
            self.grid[r][c] = self.paint_value
            self.wave, self.path = None, set()
            self._redraw()

    def _redraw(self, wave_marks=None, kmax=1):
        cv = self.canvas; cv.delete("all")
        W, H = max(cv.winfo_width(), 800), max(cv.winfo_height(), 700)
        self.cell = max(14, min((W - 20) // self.cols, (H - 20) // self.rows))
        self.ox = (W - self.cell * self.cols) // 2
        self.oy = (H - self.cell * self.rows) // 2
        fsize = max(6, self.cell // 3)
        for r in range(self.rows):
            for c in range(self.cols):
                x0, y0 = self.ox + c * self.cell, self.oy + r * self.cell
                v = self.grid[r][c]
                fill, txt = (C_WALL, "-1") if v == -1 else (C_FREE, "0")
                if wave_marks and (r, c) in wave_marks:
                    k = wave_marks[(r, c)]; fill, txt = wave_color(k, kmax), str(k)
                if (r, c) in self.path:
                    fill = C_PATH
                if (r, c) == self.start:
                    fill = C_START
                if (r, c) == self.target:
                    fill = C_TARGET
                cv.create_rectangle(x0, y0, x0 + self.cell, y0 + self.cell, fill=fill, outline="#999")
                if self.show_nums.get():
                    colr = "white" if fill in (C_WALL, C_START, C_TARGET, C_PATH) else "#333"
                    cv.create_text(x0 + self.cell / 2, y0 + self.cell / 2, text=txt, fill=colr, font=("Segoe UI", fsize))

    def stop(self):
        self.animating = False
        if self.job:
            try: self.root.after_cancel(self.job)
            except Exception: pass
            self.job = None

    def run(self):
        self.stop()
        res = wave_search(self.grid, self.start, self.target, self.op_key())
        self.result = res
        self.path = set()
        marks = {}
        if self.instant.get():
            self._finish(res)
            return
        self.animating = True
        self._step(res, 0, marks)

    def _step(self, res, i, marks):
        if not self.animating:
            return
        if i >= len(res["fronts"]):
            self.animating = False; self._finish(res); return
        for cell in res["fronts"][i]:
            marks[cell] = res["wave"][cell[0]][cell[1]]
        self._redraw(marks, max(marks.values()))
        self.status.set(f"Цикл хвилі {i}: фронт містить {len(res['fronts'][i])} клітинок.")
        self.job = self.root.after(max(1, int(self.delay_var.get())), lambda: self._step(res, i + 1, marks))

    def _finish(self, res):
        marks = {(r, c): res["wave"][r][c] for r in range(self.rows) for c in range(self.cols) if res["wave"][r][c] > 0}
        self.path = set(res["path"]) if res["found"] else set()
        self._redraw(marks, max(marks.values()) if marks else 1)
        self._result_window(res)

    def _result_window(self, res):
        w = tk.Toplevel(self.root); w.title("Результат хвильового пошуку"); w.geometry("560x520")
        f = ttk.Frame(w, padding=14); f.pack(fill="both", expand=True)
        ok = res["found"]
        ttk.Label(f, text="Шлях: " + ("ЗНАЙДЕНО" if ok else "НЕ ЗНАЙДЕНО"), font=("Segoe UI", 14, "bold"),
                  foreground="#1e8449" if ok else "#c0392b").pack(anchor="w")
        ttk.Separator(f).pack(fill="x", pady=6)
        walls = sum(row.count(-1) for row in self.grid)
        info = [("Оператор переходу", OPERATORS[self.op_key()][0]),
                ("Розмір лабіринту", f"{self.rows}×{self.cols}, стін {100*walls/(self.rows*self.cols):.1f}%"),
                ("Початкова вершина (рядок, стовпець)", f"({self.start[0]+1}, {self.start[1]+1})"),
                ("Цільова вершина (рядок, стовпець)", f"({self.target[0]+1}, {self.target[1]+1})"),
                ("Довжина шляху (кроків)", str(len(res["path"]) - 1) if ok else "—"),
                ("Кількість циклів розкриття (хвиль)", str(res["cycles"])),
                ("Кількість розкритих вершин", str(res["expanded"])),
                ("Кількість позначених вершин", str(res["marked"])),
                ("Час пошуку", f"{res['time_ms']:.4f} мс")]
        for a, b in info:
            row = ttk.Frame(f); row.pack(fill="x", pady=2)
            ttk.Label(row, text=a + ":", width=36).pack(side="left")
            ttk.Label(row, text=b, font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Separator(f).pack(fill="x", pady=6)
        ttk.Label(f, text="Вершини знайденого шляху (рядок, стовпець):").pack(anchor="w")
        t = tk.Text(f, height=8, wrap="word")
        t.insert("1.0", " → ".join(f"({r+1},{c+1})" for r, c in res["path"]) if ok else "шлях відсутній")
        t.configure(state="disabled"); t.pack(fill="both")
        ttk.Button(f, text="Закрити", command=w.destroy).pack(anchor="e", pady=8)

    def compare(self):
        w = tk.Toplevel(self.root); w.title("Порівняння операторів переходу"); w.geometry("980x230")
        f = ttk.Frame(w, padding=10); f.pack(fill="both", expand=True)
        cols = ("Оператор переходу", "Знайдено?", "Довжина шляху", "Циклів", "Розкрито", "Позначено", "Час, мс")
        tv = ttk.Treeview(f, columns=cols, show="headings", height=3)
        for c in cols:
            tv.heading(c, text=c); tv.column(c, width=120, anchor="center")
        tv.column("Оператор переходу", width=260, anchor="w")
        for k, (name, _) in OPERATORS.items():
            r = wave_search(self.grid, self.start, self.target, k)
            tv.insert("", "end", values=(name, "так" if r["found"] else "ні",
                      len(r["path"]) - 1 if r["found"] else "—", r["cycles"], r["expanded"], r["marked"], f"{r['time_ms']:.4f}"))
        tv.pack(fill="both", expand=True)
        ttk.Label(f, text=f"Лабіринт {self.rows}×{self.cols}; старт ({self.start[0]+1},{self.start[1]+1}), "
                  f"ціль ({self.target[0]+1},{self.target[1]+1}).", foreground="#555").pack(anchor="w", pady=6)


def main():
    root = tk.Tk()
    try:
        s = ttk.Style()
        if "clam" in s.theme_names(): s.theme_use("clam")
    except Exception:
        pass
    WaveApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
