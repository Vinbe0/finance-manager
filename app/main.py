import streamlit as st
from core.transforms import load_seed, account_balance
from core.domain import Transaction

st.set_page_config(page_title="Finance Manager", layout="wide")


accounts, categories, transactions, budgets = load_seed("data/seed.json")

st.title("💰 Finance Manager - Overview")

st.write("### Data Summary")
st.write(f"- Accounts: {len(accounts)}")
st.write(f"- Categories: {len(categories)}")
st.write(f"- Transactions: {len(transactions)}")
st.write(f"- Budgets: {len(budgets)}")

(account_balance(transactions, acc.id) + acc.balance for acc in accounts)
st.metric("Total Balance", f"{total_balance} KZT")
