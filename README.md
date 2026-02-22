See [DESIGN.md](DESIGN.md) for details.
---
## 🚀 Quickstart

### 🧰 Setup

This project uses **Python 3.14.3** (Homebrew path: `/opt/homebrew/bin/python3`).

1. Create a virtual environment:

```bash
python3 -m venv .venv
```

2. Activate the virtual environment:

```bash
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

---

### ▶️ Run the main ingestion pipeline

```bash
./.venv/bin/python main.py
```

---

### 🧪 Use clients

**Option 1 — Jupyter notebook**

```bash
jupyter notebook
```

Then navigate to:

```
clients/demo.ipynb
```

**Option 2 — Loader script**

```bash
./.venv/bin/python client/loader.py
```

---

### ✅ Notes

* Make sure you’re inside the virtual environment before running commands.
* Paths assume you’re running from the project root.
