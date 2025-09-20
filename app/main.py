import streamlit as st
import core.transforms
import sys

print("DEBUG - transforms loaded from:", core.transforms.__file__)
print("DEBUG - sys.path:", sys.path)

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
st.write("DEBUG:", accounts, categories, transactions, budgets)

st.metric("Total Balance", f"{total_balance} KZT")
