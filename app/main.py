import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time
from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import load_seed, account_balance
from core.transforms import (
    income_transactions,
    expense_transactions,
    transaction_amounts,
)
from core.memo import forecast_expenses

st.set_page_config(page_title="Finance Manager", layout="wide")

accounts, categories, transactions, budgets = load_seed("data/seed.json")

def tx_to_df(tx_list):
    rows = []
    for t in tx_list:
        d = t.__dict__ if not isinstance(t, dict) else t
        amount = None
        for k in ("amount", "value", "sum", "amt"):
            if k in d and d[k] is not None:
                amount = d[k]
                break
        try:
            amount = float(amount or 0)
        except:
            amount = 0.0
        date = d.get("date") or d.get("created_at") or d.get("timestamp")
        rows.append({
            "date": pd.to_datetime(date, errors="coerce"),
            "amount": amount,
            "category_id": d.get("category_id") or d.get("category") or None,
            "account_id": d.get("account_id") or d.get("account") or None,
            **{k: v for k, v in d.items()}
        })
    df = pd.DataFrame(rows)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

df = tx_to_df(transactions)

if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame(columns=["date", "amount", "category", "account", "description"])

menu = st.sidebar.radio(
    "Меню",
    ["🏠 Overview", "📂 Data", "✏️ Input Data", "⚙️ Functional Core", "🔁 Pipelines", "📈 Reports"]
)

if menu == "🏠 Overview":
    total_balance = sum(account_balance(transactions, acc.id) for acc in accounts)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Accounts", len(accounts))
    with k2:
        st.metric("Categories", len(categories))
    with k3:
        st.metric("Transactions", len(transactions))
    with k4:
        st.metric("Total Balance", f"{total_balance:,.0f} KZT")

    accounts_names = [a.name for a in accounts]
    balances = [account_balance(transactions, a.id) for a in accounts]
    fig_bal = px.bar(
        x=accounts_names,
        y=balances,
        labels={"x": "Account", "y": "Balance (KZT)"},
        title="Баланс по аккаунтам",
        template="plotly_dark"
    )
    st.plotly_chart(fig_bal, use_container_width=True)

    end = pd.Timestamp.today().normalize()
    months = pd.date_range(end=end, periods=12, freq="M")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if not df.empty and df["date"].notna().any():
        inc_m = df[df["amount"] > 0].set_index("date").resample("M")["amount"].sum().reindex(months, fill_value=0)
        exp_m = (-df[df["amount"] < 0].set_index("date").resample("M")["amount"].sum()).reindex(months, fill_value=0)
    else:
        inc_m = pd.Series(np.zeros(len(months)), index=months)
        exp_m = pd.Series(np.zeros(len(months)), index=months)

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=[m.strftime("%b %y") for m in months], y=inc_m.values, mode="lines+markers", name="Income"))
    fig_ts.add_trace(go.Scatter(x=[m.strftime("%b %y") for m in months], y=exp_m.values, mode="lines+markers", name="Expense"))
    fig_ts.update_layout(template="plotly_dark", margin=dict(t=30, b=10, l=10, r=10))
    st.plotly_chart(fig_ts, use_container_width=True)

    if not df.empty:
        df_top = df.assign(abs_amount=df["amount"].abs()).sort_values("abs_amount", ascending=False).head(8)
        disp = df_top[["date", "amount", "category_id", "account_id"]].copy()
        disp["date"] = pd.to_datetime(disp["date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("-")
        disp["amount"] = disp["amount"].fillna(0).map(lambda x: f"{x:,.0f} KZT")
        st.subheader("📊 Топ транзакций")
        st.table(disp.reset_index(drop=True))
        csv = disp.to_csv(index=False)
        st.download_button("⬇ Скачать CSV", csv, file_name="top_transactions.csv")
    else:
        st.info("Нет транзакций для отображения.")

elif menu == "📂 Data":
    st.title("📂 Data Overview")
    with st.expander("Accounts"):
        st.json([a.__dict__ for a in accounts])
    with st.expander("Categories"):
        st.json([c.__dict__ for c in categories])
    with st.expander("Transactions (first 20)"):
        st.json([t.__dict__ for t in transactions[:20]])
    with st.expander("Budgets"):
        st.json([b.__dict__ for b in budgets])

elif menu == "✏️ Input Data":
    st.title("✏️ Ввод новой транзакции")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Дата")
            amount = st.number_input("Сумма (KZT)", step=100.0, format="%.2f")
        with col2:
            category = st.selectbox("Категория", [c.name for c in categories])
            account = st.selectbox("Аккаунт", [a.name for a in accounts])
        description = st.text_input("Описание (необязательно)")
        submitted = st.form_submit_button("Добавить")

        if submitted:
            new_row = {
                "date": pd.to_datetime(date),
                "amount": amount,
                "category": category,
                "account": account,
                "description": description,
            }
            st.session_state.manual_df = pd.concat([st.session_state.manual_df, pd.DataFrame([new_row])], ignore_index=True)
            st.success("✅ Транзакция добавлена!")

    if not st.session_state.manual_df.empty:
        st.subheader("📋 Введённые транзакции")
        disp = st.session_state.manual_df.copy()
        disp["date"] = pd.to_datetime(disp["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        disp["amount"] = disp["amount"].map(lambda x: f"{x:,.0f} KZT")
        st.table(disp)
        csv = disp.to_csv(index=False)
        st.download_button("⬇ Скачать CSV", csv, file_name="manual_transactions.csv")

elif menu == "⚙️ Functional Core":
    from core.recursion import by_category, by_date_range, by_amount_range
    from core.functional import safe_category, validate_transaction, check_budget
    from core.domain import Transaction
    
    st.title("⚙️ Functional Core")
    
    # Lab #4 - Functional Patterns Section
    st.subheader("🔧 Lab #4 - Functional Patterns (Maybe/Either)")
    
    # Validation Pipeline Demo
    st.write("**Pipeline валидации транзакции:**")
    
    # Create a test transaction for validation
    test_transaction = Transaction(
        id="test_tx",
        account_id=accounts[0].id,
        cat_id=categories[0].id,
        amount=-1000,
        ts="2025-01-01",
        note="Test transaction"
    )
    
    # Step 1: Check if account exists
    st.write("1. **Проверка существования счёта:**")
    account_exists = any(acc.id == test_transaction.account_id for acc in accounts)
    if account_exists:
        st.success(f"✅ Счёт найден: {accounts[0].name}")
    else:
        st.error("❌ Счёт не найден")
    
    # Step 2: Check if category exists using safe_category
    st.write("2. **Проверка существования категории:**")
    category_result = safe_category(categories, test_transaction.cat_id)
    if category_result.is_some():
        category = category_result.get_or_else(None)
        st.success(f"✅ Категория найдена: {category.name}")
    else:
        st.error("❌ Категория не найдена")
    
    # Step 3: Validate transaction using Either
    st.write("3. **Валидация транзакции:**")
    validation_result = validate_transaction(test_transaction, accounts, categories)
    if validation_result.is_right():
        st.success("✅ Транзакция валидна")
    else:
        error = validation_result.get_error()
        st.error(f"❌ Ошибка валидации: {error['message']}")
    
    # Step 4: Check budget using Either
    st.write("4. **Проверка бюджета:**")
    if budgets:
        budget_result = check_budget(budgets[0], transactions)
        if budget_result.is_right():
            st.success(f"✅ Бюджет не превышен для категории {budgets[0].cat_id}")
        else:
            error = budget_result.get_error()
            st.error(f"❌ Бюджет превышен: {error['message']}")
            st.write(f"Лимит: {error['limit']:,} KZT")
            st.write(f"Потрачено: {error['spent']:,} KZT")
            st.write(f"Превышение: {error['over_budget']:,} KZT")
    else:
        st.info("Нет бюджетов для проверки")
    
    st.divider()
    
    # Original Functional Core content
    st.subheader("🔧 Лабы 1-3 - Функциональные трансформации")
    food_id = categories[0].id
    food_trans = list(filter(by_category(food_id), transactions))
    st.write(f"Транзакций в категории {categories[0].name}: {len(food_trans)}")
    date_trans = list(filter(by_date_range("2024-01-01", "2024-12-31"), transactions))
    st.write(f"Транзакций за 2024 год: {len(date_trans)}")
    amount_trans = list(filter(by_amount_range(-5000, -1000), transactions))
    st.write(f"Расходов от -5000 до -1000: {len(amount_trans)}")
    st.write(f"Доходных транзакций: {len(income_transactions(transactions))}")
    st.write(f"Расходных транзакций: {len(expense_transactions(transactions))}")
    st.write(f"Первые 5 сумм: {transaction_amounts(transactions)[:5]}")
    acc = accounts[0]
    st.write(f"Баланс первого аккаунта ({acc.name}): {account_balance(transactions, acc.id):,} KZT")

elif menu == "🔁 Pipelines":
    st.title("🔁 Pipelines & Recursion")
    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Выберите категорию", list(cat_names.keys()))
    selected_id = cat_names[selected_name]
    subs = flatten_categories(categories, selected_id)
    total = sum_expenses_recursive(categories, transactions, selected_id)
    st.write(f"Подкатегории категории {selected_name}:")
    for c in subs:
        st.write(f"- {c.name}")
    st.metric("Сумма расходов (с учётом подкатегорий)", f"{abs(total):,} KZT")

elif menu == "📈 Reports":
    st.title("📈 Reports — Forecast")
    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Выберите категорию", list(cat_names.keys()))
    selected_id = cat_names[selected_name]
    start = time.time()
    result1 = forecast_expenses(selected_id, tuple(transactions), 6)
    uncached_time = (time.time() - start) * 1000
    start = time.time()
    result2 = forecast_expenses(selected_id, tuple(transactions), 6)
    cached_time = (time.time() - start) * 1000
    st.metric("Прогноз расходов", f"{result2:,.0f} KZT")
    st.caption(f"⏱ Без кэша: {uncached_time:.3f} ms | С кэшем: {cached_time:.3f} ms")
