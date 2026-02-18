# 💰 Darrian's Personal Budget Dashboard

A Streamlit-based personal finance tracker built around your real budget categories, income, and 404 Sole Archive resale business.

---

## 🚀 Setup (Do This Once)

### 1. Prerequisites
- Python 3.10+ installed
- VS Code with the Python extension

### 2. Clone / open this folder in VS Code
Open the `darrian-budget` folder in VS Code.

### 3. Create a virtual environment
In VS Code's terminal (`Ctrl + ~`):

```bash
python -m venv venv
```

Activate it:
- **Mac/Linux:** `source venv/bin/activate`
- **Windows:** `venv\Scripts\activate`

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the app
```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`

---

## 📁 Project Structure

```
darrian-budget/
├── app.py                  # Main dashboard / overview
├── requirements.txt
├── data/
│   └── budget.db           # SQLite database (auto-created on first run)
├── pages/
│   ├── 1_expenses.py       # Enter actual spending by category
│   ├── 2_income.py         # Track income sources (salary, RSUs, etc.)
│   └── 3_sole_archive.py   # 404 Sole Archive resale tracker
└── utils/
    └── db.py               # Database setup and seed data
```

---

## 💡 How to Use

### Overview (app.py)
- Select a month from the sidebar
- See income vs expenses at a glance
- Track savings rate and which categories are over budget

### Expenses
- Your categories from your spreadsheet are pre-loaded every month
- Click cells in the **Actual ($)** column to enter what you actually spent
- Hit **Save Changes**
- Add custom rows for one-off expenses

### Income
- Your Visa take-home ($2,142) is pre-seeded each month
- Add RSU vests, ESPP payouts, or any extra income as separate rows
- 404 Sole Archive income flows from the resale tracker automatically (update manually for now)

### 404 Sole Archive
- Add each pair you buy to inventory with your cost basis
- Mark pairs as sold with sale price, platform, fees, and shipping
- See net profit per pair and total P&L

---

## 🔮 Future Upgrades
- [ ] Export monthly report to PDF
- [ ] Month-over-month trend charts
- [ ] Auto-pull 404 Sole Archive profit into income page
- [ ] Josh's rent income (add when he moves in)
- [ ] Mortgage vs current rent toggle for house hunting scenarios
