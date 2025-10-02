import streamlit as st
from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import load_seed, account_balance
from core.transforms import (
    income_transactions,
    expense_transactions,
    transaction_amounts,
)
import time
from core.memo import forecast_expenses



st.set_page_config(page_title="Finance Manager", layout="wide")

accounts, categories, transactions, budgets = load_seed("data/seed.json")

menu = st.sidebar.radio("Меню", ["Overview", "Data", "Functional Core", "Pipelines", "Reports"])

if menu == "Overview":
    st.title("💰 Finance Manager - Overview")

    total_balance = sum(account_balance(transactions, acc.id) for acc in accounts)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accounts", len(accounts))
    col2.metric("Categories", len(categories))
    col3.metric("Transactions", len(transactions))
    col4.metric("Total Balance", f"{total_balance} KZT")

elif menu == "Data":
    st.title("📂 Data")
    with st.expander("Accounts"):
        st.json([a.__dict__ for a in accounts])
    with st.expander("Categories"):
        st.json([c.__dict__ for c in categories])
    with st.expander("Transactions"):
        st.json([t.__dict__ for t in transactions[:20]])
    with st.expander("Budgets"):
        st.json([b.__dict__ for b in budgets])

elif menu == "Functional Core":
    from core.recursion import by_category, by_date_range, by_amount_range

    st.title("⚙️ Functional Core")
    st.subheader("Demo: map / filter / reduce")
    st.subheader("🔎 Filters demo")

    food_id = categories[0].id  
    food_trans = list(filter(by_category(food_id), transactions))
    st.write(f"Транзакций в категории {categories[0].name}: {len(food_trans)}")

    date_trans = list(filter(by_date_range("2024-01-01", "2024-12-31"), transactions))
    st.write(f"Транзакций за 2024 год: {len(date_trans)}")

    amount_trans = list(filter(by_amount_range(-5000, -1000), transactions))
    st.write(f"Расходов от -5000 до -1000: {len(amount_trans)}")


    st.write(f"- Доходных транзакций: {len(income_transactions(transactions))}")
    st.write(f"- Расходных транзакций: {len(expense_transactions(transactions))}")
    st.write(f"- Первые 5 сумм (map): {transaction_amounts(transactions)[:5]}")

    acc = accounts[0]
    st.write(
        f"- Баланс первого аккаунта ({acc.name}): {account_balance(transactions, acc.id)} KZT"
    )

elif menu == "Pipelines":
    st.title("📊 Pipelines & Recursion")

    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Выберите категорию", list(cat_names.keys()))
    selected_id = cat_names[selected_name]

    subs = flatten_categories(categories, selected_id)
    total = sum_expenses_recursive(categories, transactions, selected_id)

    st.write(f"Подкатегории категории **{selected_name}**:")
    for c in subs:
        st.write(f"- {c.name}")

    st.metric("Сумма расходов (с учётом подкатегорий)", f"{abs(total)} KZT")

elif menu == "Reports":
    from core.recursion import forecast_expenses
    import time

    st.title("📊 Reports - Forecast (cached)")

    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Выберите категорию", list(cat_names.keys()))
    selected_id = cat_names[selected_name]

    start = time.time()
    result1 = forecast_expenses(selected_id, tuple(transactions), 6)
    uncached_time = (time.time() - start) * 1000

    start = time.time()
    result2 = forecast_expenses(selected_id, tuple(transactions), 6)
    cached_time = (time.time() - start) * 1000

    st.write(f"Прогноз расходов по категории **{selected_name}** (среднее за 6 мес): {result2} KZT")
    st.write(f"⏱ Время без кэша: {uncached_time:.3f} ms")
    st.write(f"⏱ Время с кэшем: {cached_time:.3f} ms")

elif menu == "Reports":
    st.title("📊 Reports: Forecast with Cache")

    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Выберите категорию", list(cat_names.keys()))
    selected_id = cat_names[selected_name]

    start = time.time()
    forecast1 = forecast_expenses(selected_id, transactions, 5)
    first_time = (time.time() - start) * 1000  

    start = time.time()
    forecast2 = forecast_expenses(selected_id, transactions, 5)
    second_time = (time.time() - start) * 1000  

    st.metric("Прогноз расходов (среднее за 5 транзакций)", f"{forecast2} KZT")
    st.write(f"⏱ Первый вызов: {first_time:.3f} ms")
    st.write(f"⚡ Второй вызов (из кэша): {second_time:.3f} ms")

