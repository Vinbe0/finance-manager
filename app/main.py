import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

# Import the event system
from core.events import (
    event_bus,
    TRANSACTION_ADDED,
    BUDGET_ALERT,
    BALANCE_ALERT,
    register_default_handlers
)
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
st.sidebar.markdown("### 👤 Profile")
nickname = st.sidebar.text_input("Nickname", value=st.session_state.get("nickname", ""))
st.session_state["nickname"] = nickname
if nickname:
    st.sidebar.caption(f"Hello, {nickname}!")


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
    "Menu",
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
        title="Account Balances",
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
        st.subheader("📊 Top Transactions")
        st.table(disp.reset_index(drop=True))
        csv = disp.to_csv(index=False)
        st.download_button("⬇ Download CSV", csv, file_name="top_transactions.csv")
    else:
        st.info("No transactions to display.")

elif menu == "📂 Data":
    st.title("📂 Data Overview")
    
    # Accounts Section
    st.header("💳 Accounts")
    account_cols = st.columns(len(accounts))
    for idx, (col, acc) in enumerate(zip(account_cols, accounts)):
        with col:
            st.metric(
                acc.name,
                f"{account_balance(transactions, acc.id):,.0f} KZT",
                delta=None
            )
    
    # Categories Section with Tree View
    st.header("🗂 Categories")
    cat_cols = st.columns([2, 3])
    with cat_cols[0]:
        selected_cat = st.selectbox(
            "Select Category",
            options=[c.name for c in categories],
            index=0
        )
        selected_cat_id = next(c.id for c in categories if c.name == selected_cat)
        subcats = flatten_categories(categories, selected_cat_id)
        
        if subcats:
            st.markdown("**Subcategories:**")
            for sub in subcats:
                st.markdown(f"- {sub.name}")
    
    with cat_cols[1]:
        # Show category spending distribution
        cat_expenses = []
        for cat in categories:
            total = sum_expenses_recursive(categories, transactions, cat.id)
            if total != 0:  # Only include categories with transactions
                cat_expenses.append({"Category": cat.name, "Total": abs(total)})
        
        if cat_expenses:
            df_cat = pd.DataFrame(cat_expenses)
            fig_cat = px.pie(
                df_cat,
                values="Total",
                names="Category",
                title="Category Distribution"
            )
            fig_cat.update_layout(height=300)
            st.plotly_chart(fig_cat, use_container_width=True)
    
    # Transactions Section
    st.header("💸 Transactions")
    
    # Transaction filters
    col1, col2, col3 = st.columns(3)
    with col1:
        # Handle date range with proper NaT checking
        dates = pd.to_datetime(df["date"])
        valid_dates = dates[dates.notna()]
        
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
        else:
            min_date = pd.Timestamp.today().date()
            max_date = pd.Timestamp.today().date()
            
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            key="tx_date_range"
        )
    with col2:
        selected_account = st.multiselect(
            "Account",
            options=[a.name for a in accounts],
            default=[]
        )
    with col3:
        selected_category = st.multiselect(
            "Category",
            options=[c.name for c in categories],
            default=[]
        )
    
    # Filter transactions
    filtered_df = df.copy()
    if len(date_range) == 2:
        # Convert date_range to datetime for proper comparison
        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1])
        
        # Handle NaT values in date filtering
        filtered_df = filtered_df[
            filtered_df["date"].notna() &
            (filtered_df["date"] >= start_date) &
            (filtered_df["date"] <= end_date)
        ]
    if selected_account:
        filtered_df = filtered_df[filtered_df["account_id"].isin(
            [a.id for a in accounts if a.name in selected_account]
        )]
    if selected_category:
        filtered_df = filtered_df[filtered_df["category_id"].isin(
            [c.id for c in categories if c.name in selected_category]
        )]
    
    # Display transactions
    if not filtered_df.empty:
        display_df = (
            filtered_df[["date", "amount", "category_id", "account_id", "note"]]
            .assign(
                date=lambda x: x["date"].apply(lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "N/A"),
                amount=lambda x: x["amount"].map(lambda v: f"{v:,.0f} KZT" if pd.notna(v) else "N/A")
            )
            .rename(columns={
                "category_id": "Category",
                "account_id": "Account",
                "note": "Note"
            })
        )
        
        # Download filtered data
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download Filtered Data",
            csv,
            file_name="transactions_filtered.csv",
            mime="text/csv"
        )
    else:
        st.info("No transactions match the selected filters")
    
    # Budgets Section
    st.header("💰 Budgets")
    if budgets:
        budget_data = []
        for budget in budgets:
            cat_name = next((c.name for c in categories if c.id == budget.cat_id), "Unknown")
            spent = sum(t.amount for t in transactions if t.cat_id == budget.cat_id and t.amount < 0)
            remaining = budget.limit + spent  # spent is negative
            progress = min(100, max(0, (abs(spent) / budget.limit) * 100))
            
            budget_data.append({
                "Category": cat_name,
                "Limit": budget.limit,
                "Spent": abs(spent),
                "Remaining": remaining,
                "Progress": progress
            })
        
        budget_df = pd.DataFrame(budget_data)
        for _, row in budget_df.iterrows():
            st.metric(
                f"Budget: {row['Category']}",
                f"{row['Spent']:,.0f} / {row['Limit']:,.0f} KZT",
                f"{row['Remaining']:,.0f} KZT remaining"
            )
            st.progress(row['Progress'] / 100)
    else:
        st.info("No budgets defined")

elif menu == "🧾 Transactions":
    from core.events import event_bus, TRANSACTION_ADDED, BUDGET_ALERT, BALANCE_ALERT

    # Initialize session state for alerts
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []

    st.title("🧾 New Transaction")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            amount = st.number_input("Amount (KZT)", step=100.0, format="%.2f")
        with col2:
            category = st.selectbox("Category", [c.name for c in categories])
            account = st.selectbox("Account", [a.name for a in accounts])
        description = st.text_input("Description (optional)")
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
        st.subheader("📋 Entered Transactions")
        disp = st.session_state.manual_df.copy()
        disp["date"] = pd.to_datetime(disp["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        disp["amount"] = disp["amount"].map(lambda x: f"{x:,.0f} KZT")
        st.table(disp)
        csv = disp.to_csv(index=False)
        st.download_button("⬇ Download CSV", csv, file_name="manual_transactions.csv")

elif menu == "✅ Validation":
    from core.recursion import by_category, by_date_range, by_amount_range
    from core.functional import safe_category, validate_transaction, check_budget
    from core.domain import Transaction
    
    st.title("✅ Validation & Budgets")
    if nickname:
        st.caption(f"Working for user: {nickname}")
    
    st.write("**Transaction and Budget Validation**")
    with st.form("validation_pipeline"):
        col1, col2, col3 = st.columns(3)
        with col1:
            acc_name = st.selectbox("Account", [a.name for a in accounts])
            acc_id = next(a.id for a in accounts if a.name == acc_name)
        with col2:
            cat_name = st.selectbox("Category", [c.name for c in categories])
            cat_id = next(c.id for c in categories if c.name == cat_name)
        with col3:
            amount = st.number_input("Amount (− expense, + income)", value=-1000, step=100)
        date = st.date_input("Transaction Date")
        note = st.text_input("Note", value="Demo")
        run_validation = st.form_submit_button("Validate")
    
    if run_validation:
        test_transaction = Transaction(
            id="test_tx",
            account_id=acc_id,
            cat_id=cat_id,
            amount=int(amount),
            ts=str(date),
            note=note,
        )
        
        st.write("1. **Account Existence Check:**")
        account_exists = any(acc.id == test_transaction.account_id for acc in accounts)
        if account_exists:
            st.success(f"✅ Account found: {acc_name}")
        else:
            st.error("❌ Account not found")
        
        st.write("2. **Category Existence Check:**")
        category_result = safe_category(categories, test_transaction.cat_id)
        if category_result.is_some():
            category = category_result.get_or_else(None)
            st.success(f"✅ Category found: {category.name}")
        else:
            st.error("❌ Category not found")
        
        st.write("3. **Transaction Validation:**")
        validation_result = validate_transaction(test_transaction, accounts, categories)
        if validation_result.is_right():
            st.success("✅ Transaction is valid")
        else:
            error = validation_result.get_error()
            st.error(f"❌ Validation error: {error['message']}")
        
        st.write("4. **Budget Check:**")
        if budgets:
            b_names = [f"{b.id} ({b.cat_id})" for b in budgets]
            b_choice = st.selectbox("Select budget to check", b_names, key="budget_choice")
            b_idx = b_names.index(b_choice)
            budget_result = check_budget(budgets[b_idx], transactions)
            if budget_result.is_right():
                st.success(f"✅ Budget not exceeded for category {budgets[b_idx].cat_id}")
            else:
                error = budget_result.get_error()
                st.error(f"❌ Budget exceeded: {error['message']}")
                st.write(f"Limit: {error['limit']:,} KZT")
                st.write(f"Spent: {error['spent']:,} KZT")
                st.write(f"Over budget: {error['over_budget']:,} KZT")
        else:
            st.info("No budgets to check")
    
    st.divider()
    
    # Quick filters and statistics
    st.subheader("Filters and Statistics")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        cat_name_fc = st.selectbox("Filter by Category", [c.name for c in categories], key="fc_cat")
        food_id = next(c.id for c in categories if c.name == cat_name_fc)
    with col_b:
        start_date = st.text_input("Start Date (YYYY-MM-DD)", value="2024-01-01")
    with col_c:
        end_date = st.text_input("End Date (YYYY-MM-DD)", value="2024-12-31")

    from core.recursion import by_category, by_date_range, by_amount_range
    food_trans = list(filter(by_category(food_id), transactions))
    st.write(f"Transactions in category {cat_name_fc}: {len(food_trans)}")
    date_trans = list(filter(by_date_range(start_date, end_date), transactions))
    st.write(f"Transactions in period: {len(date_trans)}")
    amount_trans = list(filter(by_amount_range(-5000, -1000), transactions))
    st.write(f"Expenses between -5000 and -1000: {len(amount_trans)}")
    st.write(f"Income transactions: {len(income_transactions(transactions))}")
    st.write(f"Expense transactions: {len(expense_transactions(transactions))}")
    st.write(f"First 5 amounts: {transaction_amounts(transactions)[:5]}")
    acc = st.selectbox("Select account for balance", [a.name for a in accounts], key="acc_balance")
    acc_id = next(a.id for a in accounts if a.name == acc)
    st.write(f"Selected account balance ({acc}): {account_balance(transactions, acc_id):,} KZT")

elif menu == "📊 Analytics":
    from core.lazy import iter_transactions, lazy_top_categories
    
    st.title("📊 Analytics")

    # Categories and Subcategories
    st.subheader("Category Structure and Expenses")
    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Category", list(cat_names.keys()))
    selected_id = cat_names[selected_name]
    subs = flatten_categories(categories, selected_id)
    total = sum_expenses_recursive(categories, transactions, selected_id)
    st.write(f"Subcategories of {selected_name}:")
    for c in subs:
        st.write(f"- {c.name}")
    st.metric("Total Expenses (including subcategories)", f"{abs(total):,} KZT")

    st.divider()

    # Expense Forecast
    st.subheader("Category Expense Forecast")
    start_t = time.time()
    _ = forecast_expenses(selected_id, tuple(transactions), 6)
    uncached_time = (time.time() - start_t) * 1000
    start_t = time.time()
    forecast_value = forecast_expenses(selected_id, tuple(transactions), 6)
    cached_time = (time.time() - start_t) * 1000
    st.metric("Forecasted Expenses", f"{forecast_value:,.0f} KZT")
    st.caption(f"⏱ Without cache: {uncached_time:.3f} ms | With cache: {cached_time:.3f} ms")

    st.divider()

    # Lazy Processing and Top Categories
    st.subheader("Lazy Processing and Top Expense Categories")
    k = st.number_input("Show top-K categories:", min_value=1, max_value=20, value=5, key="top_k_analytics")
    if st.button("Calculate Top Categories", key="btn_top_k_analytics"):
        expense_gen = iter_transactions(transactions, lambda t: t.amount < 0)
        top_cats = list(lazy_top_categories(expense_gen, categories, k))
        if top_cats:
            st.success(f"Top {len(top_cats)} Categories by Expenses")
            st.table({"Category": [n for n, _ in top_cats], "Amount": [f"{v:,}" for _, v in top_cats]})
        else:
            st.info("No data to analyze")
