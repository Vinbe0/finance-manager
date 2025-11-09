import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# Global sidebar nickname
st.sidebar.markdown("### 👤 Профиль")
nickname = st.sidebar.text_input("Никнейм", value=st.session_state.get("nickname", ""))
st.session_state["nickname"] = nickname
if nickname:
    st.sidebar.caption(f"Привет, {nickname}!")


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
    ["🏠 Overview", "📂 Data", "🧾 Transactions", "✅ Validation", "📊 Analytics"]
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

elif menu == "🧾 Transactions":
    from core.events import event_bus, TRANSACTION_ADDED, BUDGET_ALERT, BALANCE_ALERT

    # Initialize session state for alerts
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []

    st.title("🧾 Ввод новой транзакции")
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
            
            # Publish transaction event
            state = {
                "budget_limit": 10000,  # Example budget limit
                "balance_threshold": 1000,  # Example balance threshold
                "balance": st.session_state.get("current_balance", 0)
            }
            
            results = event_bus.publish(TRANSACTION_ADDED, new_row)
            
            # Update state based on event results
            for result in results:
                if "balance" in result:
                    st.session_state.current_balance = result["balance"]
                if "alert" in result:
                    st.session_state.alerts.append(result["alert"])
            
            # Check balance and publish alert if needed
            balance_results = event_bus.publish(BALANCE_ALERT, {"balance": st.session_state.current_balance})
            for result in balance_results:
                if "alert" in result:
                    st.session_state.alerts.append(result["alert"])
            
            st.session_state.manual_df = pd.concat([st.session_state.manual_df, pd.DataFrame([new_row])], ignore_index=True)
            st.success("✅ Транзакция добавлена!")

    # Display Alerts
    if st.session_state.alerts:
        st.subheader("⚠️ Alerts")
        for alert in st.session_state.alerts:
            st.warning(alert)
        if st.button("Clear Alerts"):
            st.session_state.alerts = []

    if not st.session_state.manual_df.empty:
        st.subheader("📋 Введённые транзакции")
        disp = st.session_state.manual_df.copy()
        disp["date"] = pd.to_datetime(disp["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        disp["amount"] = disp["amount"].map(lambda x: f"{x:,.0f} KZT")
        st.table(disp)
        csv = disp.to_csv(index=False)
        st.download_button("⬇ Скачать CSV", csv, file_name="manual_transactions.csv")

elif menu == "✅ Validation":
    from core.recursion import by_category, by_date_range, by_amount_range
    from core.functional import safe_category, validate_transaction, check_budget
    from core.domain import Transaction
    
    st.title("✅ Validation & Budgets")
    if nickname:
        st.caption(f"Работает для пользователя: {nickname}")
    
    st.write("**Проверка транзакции и бюджета**")
    with st.form("validation_pipeline"):
        col1, col2, col3 = st.columns(3)
        with col1:
            acc_name = st.selectbox("Счёт", [a.name for a in accounts])
            acc_id = next(a.id for a in accounts if a.name == acc_name)
        with col2:
            cat_name = st.selectbox("Категория", [c.name for c in categories])
            cat_id = next(c.id for c in categories if c.name == cat_name)
        with col3:
            amount = st.number_input("Сумма (− расход, + доход)", value=-1000, step=100)
        date = st.date_input("Дата транзакции")
        note = st.text_input("Комментарий", value="Demo")
        run_validation = st.form_submit_button("Проверить")
    
    if run_validation:
        test_transaction = Transaction(
            id="test_tx",
            account_id=acc_id,
            cat_id=cat_id,
            amount=int(amount),
            ts=str(date),
            note=note,
        )
        
        st.write("1. **Проверка существования счёта:**")
        account_exists = any(acc.id == test_transaction.account_id for acc in accounts)
        if account_exists:
            st.success(f"✅ Счёт найден: {acc_name}")
        else:
            st.error("❌ Счёт не найден")
        
        st.write("2. **Проверка существования категории:**")
        category_result = safe_category(categories, test_transaction.cat_id)
        if category_result.is_some():
            category = category_result.get_or_else(None)
            st.success(f"✅ Категория найдена: {category.name}")
        else:
            st.error("❌ Категория не найдена")
        
        st.write("3. **Валидация транзакции:**")
        validation_result = validate_transaction(test_transaction, accounts, categories)
        if validation_result.is_right():
            st.success("✅ Транзакция валидна")
        else:
            error = validation_result.get_error()
            st.error(f"❌ Ошибка валидации: {error['message']}")
        
        st.write("4. **Проверка бюджета:**")
        if budgets:
            b_names = [f"{b.id} ({b.cat_id})" for b in budgets]
            b_choice = st.selectbox("Выберите бюджет для проверки", b_names, key="budget_choice")
            b_idx = b_names.index(b_choice)
            budget_result = check_budget(budgets[b_idx], transactions)
            if budget_result.is_right():
                st.success(f"✅ Бюджет не превышен для категории {budgets[b_idx].cat_id}")
            else:
                error = budget_result.get_error()
                st.error(f"❌ Бюджет превышен: {error['message']}")
                st.write(f"Лимит: {error['limit']:,} KZT")
                st.write(f"Потрачено: {error['spent']:,} KZT")
                st.write(f"Превышение: {error['over_budget']:,} KZT")
        else:
            st.info("Нет бюджетов для проверки")
    
    st.divider()
    
    # Быстрые фильтры и статистика
    st.subheader("Фильтры и статистика")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        cat_name_fc = st.selectbox("Категория для фильтра", [c.name for c in categories], key="fc_cat")
        food_id = next(c.id for c in categories if c.name == cat_name_fc)
    with col_b:
        start_date = st.text_input("Начало периода (YYYY-MM-DD)", value="2024-01-01")
    with col_c:
        end_date = st.text_input("Конец периода (YYYY-MM-DD)", value="2024-12-31")

    from core.recursion import by_category, by_date_range, by_amount_range
    food_trans = list(filter(by_category(food_id), transactions))
    st.write(f"Транзакций в категории {cat_name_fc}: {len(food_trans)}")
    date_trans = list(filter(by_date_range(start_date, end_date), transactions))
    st.write(f"Транзакций за период: {len(date_trans)}")
    amount_trans = list(filter(by_amount_range(-5000, -1000), transactions))
    st.write(f"Расходов от -5000 до -1000: {len(amount_trans)}")
    st.write(f"Доходных транзакций: {len(income_transactions(transactions))}")
    st.write(f"Расходных транзакций: {len(expense_transactions(transactions))}")
    st.write(f"Первые 5 сумм: {transaction_amounts(transactions)[:5]}")
    acc = st.selectbox("Аккаунт для баланса", [a.name for a in accounts], key="acc_balance")
    acc_id = next(a.id for a in accounts if a.name == acc)
    st.write(f"Баланс выбранного аккаунта ({acc}): {account_balance(transactions, acc_id):,} KZT")

elif menu == "📊 Analytics":
    from core.lazy import iter_transactions, lazy_top_categories
    
    st.title("📊 Analytics")

    # Категории и подкатегории
    st.subheader("Структура категорий и расходы")
    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Категория", list(cat_names.keys()))
    selected_id = cat_names[selected_name]
    subs = flatten_categories(categories, selected_id)
    total = sum_expenses_recursive(categories, transactions, selected_id)
    st.write(f"Подкатегории категории {selected_name}:")
    for c in subs:
        st.write(f"- {c.name}")
    st.metric("Сумма расходов (с учётом подкатегорий)", f"{abs(total):,} KZT")

    st.divider()

    # Прогноз расходов
    st.subheader("Прогноз расходов по категории")
    start_t = time.time()
    _ = forecast_expenses(selected_id, tuple(transactions), 6)
    uncached_time = (time.time() - start_t) * 1000
    start_t = time.time()
    forecast_value = forecast_expenses(selected_id, tuple(transactions), 6)
    cached_time = (time.time() - start_t) * 1000
    st.metric("Прогноз расходов", f"{forecast_value:,.0f} KZT")
    st.caption(f"⏱ Без кэша: {uncached_time:.3f} ms | С кэшем: {cached_time:.3f} ms")

    st.divider()

    # Ленивая обработка и топ-категории
    st.subheader("Ленивая обработка и топ-категории по расходам")
    k = st.number_input("Показать топ-K категорий:", min_value=1, max_value=20, value=5, key="top_k_analytics")
    if st.button("Вычислить топ-категории", key="btn_top_k_analytics"):
        expense_gen = iter_transactions(transactions, lambda t: t.amount < 0)
        top_cats = list(lazy_top_categories(expense_gen, categories, k))
        if top_cats:
            st.success(f"Топ-{len(top_cats)} категорий по расходам")
            st.table({"Категория": [n for n, _ in top_cats], "Сумма": [f"{v:,}" for _, v in top_cats]})
        else:
            st.info("Нет данных для анализа")
