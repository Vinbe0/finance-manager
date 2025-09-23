import streamlit as st
from core.transforms import load_seed, account_balance
from core.transforms import income_transactions, expense_transactions, transaction_amounts


st.set_page_config(page_title="Finance Manager", layout="wide")

accounts, categories, transactions, budgets = load_seed("data/seed.json")

menu = st.sidebar.radio("Меню", ["Overview", "Data", "Functional Core"])

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
    st.title("⚙️ Functional Core")
    st.subheader("Demo: map / filter / reduce")

    st.write(f"- Доходных транзакций: {len(income_transactions(transactions))}")
    st.write(f"- Расходных транзакций: {len(expense_transactions(transactions))}")
    st.write(f"- Первые 5 сумм (map): {transaction_amounts(transactions)[:5]}")

    acc = accounts[0]
    st.write(f"- Баланс первого аккаунта ({acc.name}): {account_balance(transactions, acc.id)} KZT")

