## How to Run (Step-by-step)

### 1) Create a virtual environment (optional but recommended)

```bash
python -m venv venv
```

Activate it:

* **macOS / Linux**

  ```bash
  source venv/bin/activate
  ```

* **Windows (PowerShell / CMD)**

  ```bash
  venv\Scripts\activate
  ```

### 2) Install dependencies (based on imports in the code)

This repo does **not** include a `requirements.txt`.
Install packages based on the `import ...` statements used in `app.py` and the Jupyter notebooks (`*.ipynb`).

A typical setup might include:

```bash
pip install pandas numpy scikit-learn flask jupyter
```

If you hit `ModuleNotFoundError`, install the missing package and retry:

```bash
pip install <missing-package-name>
```

### 3) Run the notebooks first (IMPORTANT)

Run the Jupyter notebooks to generate the cleaned/merged dataset used by the Flask app.

To start Jupyter:

```bash
jupyter notebook
```

After the notebooks finish, you should have a merged/cleaned dataset available (e.g. `merged*.csv`).

### 4) Run the Flask app

```bash
python app.py
```

Then open:

* `http://127.0.0.1:5000/`

---

## Key Deliverables

* Cleaned, analysis-ready dataset created from Yelp JSON
* Market performance diagnostics to highlight:

  * regional underperformance patterns
  * customer experience / sentiment gaps
* A simple Flask-based interface to view results

---

## Notes

* File paths and dataset names may differ depending on where you store the Yelp JSON.
* To make this repo more recruiter-ready, add screenshots of your dashboard/results here.

---
