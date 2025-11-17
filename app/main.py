import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

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
from core.domain import Transaction
from uuid import uuid4
from core.transforms import (
    income_transactions,
    expense_transactions,
    transaction_amounts,
)
from core.memo import forecast_expenses
from core.services import BudgetService, ReportService

st.set_page_config(page_title="Finance Manager", layout="wide")

accounts, categories, transactions, budgets = load_seed("data/seed.json")


if "tx_transactions" not in st.session_state:
    st.session_state.tx_transactions = transactions

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

df = tx_to_df(st.session_state.tx_transactions)

if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame(columns=["date", "amount", "category", "account", "description"])


if "tx_account_balances" not in st.session_state:
    st.session_state.tx_account_balances = {
        a.id: account_balance(st.session_state.tx_transactions, a.id) for a in accounts
    }

if "tx_account_thresholds" not in st.session_state:
    st.session_state.tx_account_thresholds = {a.id: 1000 for a in accounts}

if "tx_balance" not in st.session_state:
    st.session_state.tx_balance = sum(st.session_state.tx_account_balances.values())

menu = st.sidebar.radio(
    "Menu",
    ["🏠 Overview", "📂 Data", "🧾 Transactions", "✅ Validation", "📑 Reports", "📊 Analytics"]
)

if menu == "🏠 Overview":
    total_balance = sum(account_balance(st.session_state.tx_transactions, acc.id) for acc in accounts)
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
    balances = [account_balance(st.session_state.tx_transactions, a.id) for a in accounts]
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
    
    st.header("💳 Accounts")
    account_cols = st.columns(len(accounts))
    for idx, (col, acc) in enumerate(zip(account_cols, accounts)):
        with col:
                st.metric(
                    acc.name,
                    f"{account_balance(st.session_state.tx_transactions, acc.id):,.0f} KZT",
                    delta=None
                )
    
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
        cat_expenses = []
        for cat in categories:
            total = sum_expenses_recursive(categories, transactions, cat.id)
            if total != 0:
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
    
    st.header("💸 Transactions")
    
    col1, col2, col3 = st.columns(3)
    with col1:
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
    
    filtered_df = df.copy()
    if len(date_range) == 2:
        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1])
        
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
        
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download Filtered Data",
            csv,
            file_name="transactions_filtered.csv",
            mime="text/csv"
        )
    else:
        st.info("No transactions match the selected filters")
    
    st.header("💰 Budgets")
    if budgets:
        budget_data = []
        for budget in budgets:
            cat_name = next((c.name for c in categories if c.id == budget.cat_id), "Unknown")
            spent = sum(t.amount for t in transactions if t.cat_id == budget.cat_id and t.amount < 0)
            remaining = budget.limit + spent
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
    
    if "tx_balance" not in st.session_state:
        initial_balance_from_accounts = sum(acc.balance for acc in accounts)
        initial_balance_from_transactions = sum(account_balance(st.session_state.tx_transactions, acc.id) for acc in accounts)
        st.session_state.tx_balance = initial_balance_from_accounts if initial_balance_from_accounts > 0 else max(initial_balance_from_transactions, 5000)
    if "tx_alerts" not in st.session_state:
        st.session_state.tx_alerts = []
    if "tx_event_history" not in st.session_state:
        st.session_state.tx_event_history = []
    if "tx_budget_spent" not in st.session_state:
        st.session_state.tx_budget_spent = {}
    
    st.title("🧾 Transactions")
    
    col_settings, col_balances = st.columns([1, 3])
    with col_settings:
        st.subheader("⚙️ Alert Settings")
        balance_threshold = st.number_input(
            "Balance Alert Threshold (KZT)",
            min_value=0,
            value=1000,
            step=100,
            key="balance_alert_threshold",
            help="Alert will trigger when balance falls below this amount"
        )
        
        initial_balance_input = st.number_input(
            "Set Initial Balance (KZT)",
            min_value=0,
            value=5000,
            step=1000,
            key="initial_balance_setting",
            help="Set the starting balance for testing alerts"
        )
        
        if st.button("🔧 Reset Balance", key="btn_reset_balance"):
            st.session_state.tx_balance = initial_balance_input
            st.session_state.tx_budget_spent = {}
            st.rerun()
        
        st.caption(f"**Current Balance:** {st.session_state.tx_balance:,} KZT")
        if st.session_state.tx_balance < balance_threshold:
            st.warning(f"⚠️ Balance is below threshold of {balance_threshold:,} KZT!")
        else:
            expense_needed = st.session_state.tx_balance - balance_threshold + 1
            st.caption(f"💡 Need **{expense_needed:,} KZT** in expenses to trigger balance alert")
        st.markdown("---")
        st.markdown("**Per-account balance thresholds**")
        for a in accounts:
            key = f"th_{a.id}"
            st.session_state.tx_account_thresholds[a.id] = st.number_input(
                f"{a.name} threshold",
                min_value=0,
                value=st.session_state.tx_account_thresholds.get(a.id, 1000),
                step=100,
                key=key
            )

        if st.button("🔄 Update Balances from Transactions", key="btn_update_balances"):
            recomputed = {a.id: 0 for a in accounts}
            for t in st.session_state.tx_transactions:
                tid = t.account_id if hasattr(t, "account_id") else t.get("account_id")
                tamt = t.amount if hasattr(t, "amount") else t.get("amount", 0)
                recomputed[tid] = recomputed.get(tid, 0) + int(tamt)
            st.session_state.tx_account_balances = recomputed
            st.session_state.tx_balance = sum(recomputed.values())
            st.success("Per-account balances updated from transactions")
    
    with col_balances:
        st.subheader("📊 Live Account Balances")
        balance_cols = st.columns(len(accounts))
        for idx, (col, acc) in enumerate(zip(balance_cols, accounts)):
            with col:
                acc_balance = st.session_state.tx_account_balances.get(acc.id, 0)
                acc_thresh = st.session_state.tx_account_thresholds.get(acc.id, 0)
                delta = None
                if acc_balance < acc_thresh:
                    delta = f"Below threshold ({acc_thresh:,.0f})"
                st.metric(
                    acc.name,
                    f"{acc_balance:,.0f} KZT",
                    delta=delta
                )
    
    st.divider()
    
    st.subheader("➕ Add New Transaction")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            amount = st.number_input("Amount (KZT)", step=100.0, format="%.2f")
        with col2:
            category = st.selectbox("Category", [c.name for c in categories])
            account = st.selectbox("Account", [a.name for a in accounts])
        description = st.text_input("Description (optional)")
        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            acc_id = next(a.id for a in accounts if a.name == account)
            cat_id = next(c.id for c in categories if c.name == category)
            budget = next((b for b in budgets if b.cat_id == cat_id), None)
            
            cat_type = next((c.type for c in categories if c.id == cat_id), None)
            signed_amount = int(amount)
            if cat_type == "expense" and signed_amount > 0:
                signed_amount = -abs(signed_amount)

            new_row = {
                "date": pd.to_datetime(date),
                "amount": signed_amount,
                "category": category,
                "account": account,
                "description": description,
            }

            new_tx = Transaction(
                id=str(uuid4()),
                account_id=acc_id,
                cat_id=cat_id,
                amount=signed_amount,
                ts=pd.to_datetime(date).strftime("%Y-%m-%d"),
                note=description or ""
            )
            
            budget_limit = budget.limit if budget else 10000
            current_spent = st.session_state.tx_budget_spent.get(cat_id, 0)
            
            payload = {
                "amount": signed_amount,
                "account_id": acc_id,
                "category_id": cat_id,
                "cat_id": cat_id,
                "budget_limit": budget_limit,
                "current_spent": current_spent
            }
            
            handlers_results = event_bus.publish(TRANSACTION_ADDED, payload)


            st.session_state.tx_transactions = tuple(list(st.session_state.tx_transactions) + [new_tx])

            st.session_state.tx_account_balances[acc_id] = st.session_state.tx_account_balances.get(acc_id, 0) + signed_amount

            st.session_state.tx_balance = sum(st.session_state.tx_account_balances.values())

            alerts_triggered = []
            for result in handlers_results:
                if "balance_delta" in result:
                    pass
                if "alert" in result:
                    alert_msg = result["alert"]
                    st.session_state.tx_alerts.append({
                        "type": "Budget",
                        "message": alert_msg,
                        "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
                    })
                    alerts_triggered.append(alert_msg)
                if "spent" in result:
                    st.session_state.tx_budget_spent[cat_id] = result["spent"]

            acc_balance = st.session_state.tx_account_balances.get(acc_id, 0)
            acc_threshold = st.session_state.tx_account_thresholds.get(acc_id, 0)
            acc_balance_payload = {"balance": acc_balance, "threshold": acc_threshold}
            acc_balance_results = event_bus.publish(BALANCE_ALERT, acc_balance_payload)
            for result in acc_balance_results:
                if "alert" in result:
                    alert_msg = result["alert"]
                    st.session_state.tx_alerts.append({
                        "type": "Balance",
                        "message": alert_msg,
                        "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
                    })
                    alerts_triggered.append(alert_msg)
            
            st.session_state.tx_event_history.append({
                "event": TRANSACTION_ADDED,
                "payload": {k: v for k, v in payload.items() if k != "current_spent"},
                "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
            })
            
            st.session_state.manual_df = pd.concat([st.session_state.manual_df, pd.DataFrame([new_row])], ignore_index=True)
            
            if alerts_triggered:
                st.success(f"✅ Transaction added! {len(alerts_triggered)} alert(s) triggered.")
            else:
                st.success("✅ Transaction added!")
                
            if st.session_state.tx_balance < balance_threshold:
                st.warning(f"💰 Balance is now {st.session_state.tx_balance:,} KZT (below threshold of {balance_threshold:,} KZT)")
            
            st.rerun()
    
    st.divider()
    
    st.subheader("📋 Alert Limits Info & Debug")
    
    balance_status_col, budget_status_col = st.columns(2)
    
    with balance_status_col:
        st.write("**💰 Balance Alert Status**")
        if st.session_state.tx_balance < balance_threshold:
            st.error(f"🔴 **ALERT ACTIVE!**\nBalance: {st.session_state.tx_balance:,} KZT\nThreshold: {balance_threshold:,} KZT")
        else:
            expense_needed = st.session_state.tx_balance - balance_threshold + 1
            st.success(f"✅ Balance OK\nCurrent: {st.session_state.tx_balance:,} KZT\nThreshold: {balance_threshold:,} KZT\nNeed: **{expense_needed:,} KZT** more expenses")
    
    with budget_status_col:
        st.write("**📊 Budget Alert Status**")
        if budgets:
            budget_status_lines = []
            for budget in budgets[:3]:
                cat_name = next((c.name for c in categories if c.id == budget.cat_id), budget.cat_id)
                current_spent = st.session_state.tx_budget_spent.get(budget.cat_id, 0)
                remaining = budget.limit - current_spent
                if current_spent > budget.limit:
                    budget_status_lines.append(f"🔴 {cat_name}: **EXCEEDED** ({current_spent:,} / {budget.limit:,} KZT)")
                else:
                    budget_status_lines.append(f"✅ {cat_name}: {current_spent:,} / {budget.limit:,} KZT (need {remaining + 1:,} more)")
            st.info("\n".join(budget_status_lines) if budget_status_lines else "No spending tracked")
        else:
            st.info("No budgets defined")
    
    
    st.divider()
    
    st.subheader("⚠️ Live Alerts & Warnings")
    if st.session_state.tx_alerts:
        for alert in reversed(st.session_state.tx_alerts[-10:]):
            if alert["type"] == "Budget":
                st.warning(f"🔴 [{alert['timestamp']}] {alert['message']}")
            elif alert["type"] == "Balance":
                st.error(f"🔴 [{alert['timestamp']}] {alert['message']}")
        if st.button("Clear Alerts", key="btn_clear_tx_alerts"):
            st.session_state.tx_alerts = []
            st.rerun()
    else:
        st.info("No alerts at the moment")
    
    st.divider()
    
    st.subheader("💰 Updated Total Balance")
    st.metric("Total Balance", f"{st.session_state.tx_balance:,.0f} KZT")
    
    if st.session_state.tx_budget_spent:
        st.write("**Budget Spending by Category:**")
        for cat_id, spent in st.session_state.tx_budget_spent.items():
            cat_name = next((c.name for c in categories if c.id == cat_id), cat_id)
            budget = next((b for b in budgets if b.cat_id == cat_id), None)
            if budget:
                st.write(f"- {cat_name}: {spent:,} / {budget.limit:,} KZT")
                progress = min(100, (spent / budget.limit) * 100)
                st.progress(progress / 100)
    
    st.divider()
    
    st.subheader("📜 Event History")
    if st.session_state.tx_event_history:
        event_df = pd.DataFrame(st.session_state.tx_event_history)
        st.dataframe(event_df, use_container_width=True)
        if st.button("Clear History", key="btn_clear_tx_history"):
            st.session_state.tx_event_history = []
            st.rerun()
    else:
        st.info("No events yet. Add a transaction to see event history.")
    
    st.divider()
    
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
    st.write(f"Selected account balance ({acc}): {account_balance(st.session_state.tx_transactions, acc_id):,} KZT")

elif menu == "📑 Reports":
    st.title("📑 Reports")
    st.write("Reports — composition and modularity with OOP integration")

    # small helpers to access transaction fields generically
    def _get_amount(t):
        if hasattr(t, 'amount'):
            return getattr(t, 'amount')
        if isinstance(t, dict):
            return t.get('amount', 0)
        return 0

    def _get_catid(t):
        if hasattr(t, 'cat_id'):
            return getattr(t, 'cat_id')
        if hasattr(t, 'category_id'):
            return getattr(t, 'category_id')
        if isinstance(t, dict):
            return t.get('cat_id') or t.get('category_id') or t.get('category')
        return None

    def _get_date(t):
        if hasattr(t, 'ts'):
            return getattr(t, 'ts')
        if hasattr(t, 'date'):
            return getattr(t, 'date')
        if isinstance(t, dict):
            return t.get('date') or t.get('ts') or t.get('timestamp')
        return None

    report_type = st.selectbox("Report type", ["Budget", "Category"], index=0)
    show_steps = st.checkbox("Show intermediate steps", value=False, help="Display validators and calculator outputs")

    if report_type == "Budget":
        month = st.text_input("Month (YYYY-MM)", value=pd.Timestamp.today().strftime("%Y-%m"))

        def validator_has_budgets(m, trans, buds, cats):
            msgs = []
            if not buds:
                msgs.append("No budgets defined")
            return msgs

        def calc_budget_totals(m, trans, buds, cats, acc=None):
            totals = {}
            for b in buds:
                spent = 0
                for t in trans:
                    amt = _get_amount(t) or 0
                    d = _get_date(t)
                    dstr = str(d) if d is not None else ""
                    if dstr.startswith(m):
                        if _get_catid(t) == b.cat_id and amt < 0:
                            spent += -float(amt)
                totals[b.cat_id] = spent
            return {"budget_totals": totals}

        svc = BudgetService(validators=[validator_has_budgets], calculators=[calc_budget_totals])
        rpt = svc.monthly_report(month, st.session_state.tx_transactions, budgets, categories)

        # Top-level summary metrics (styled)
        totals = rpt['result'].get('budget_totals', {})
        total_spent = sum(totals.values())
        total_budget = sum(b.limit for b in budgets) if budgets else 0

        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            st.metric("Month", month)
            st.caption("Budgets checked: {}".format(len(rpt['validation'])))
        with col2:
            st.metric("Total Spent", f"{total_spent:,.0f} KZT")
        with col3:
            st.metric("Total Budget", f"{total_budget:,.0f} KZT")

        # show budget usage progress bars
        if totals and budgets:
            progress_rows = []
            for b in budgets:
                spent = totals.get(b.cat_id, 0)
                pct = min(100, int((spent / b.limit) * 100)) if b.limit > 0 else 0
                progress_rows.append((next((c.name for c in categories if c.id == b.cat_id), b.cat_id), spent, b.limit, pct))

            st.subheader("Budget usage")
            for name, spent, limit, pct in progress_rows:
                st.write(f"**{name}** — {spent:,.0f} / {limit:,.0f} KZT")
                st.progress(pct / 100)

            # bar chart of spending by budget category
            df_tot = pd.DataFrame([{"Category": r[0], "Spent": r[1]} for r in progress_rows])
            fig = px.bar(df_tot, x="Category", y="Spent", title="Spending by Budget Category", template="plotly_dark", color="Spent", color_continuous_scale=px.colors.sequential.Emrld)
            st.plotly_chart(fig, use_container_width=True)
            st.table(df_tot)
        else:
            st.info("No budget spending found for the selected month")

        # optional intermediate steps
        if show_steps:
            with st.expander("Intermediate steps and validation", expanded=False):
                st.subheader("Validation Messages")
                for v in rpt['validation']:
                    st.write(v)
                st.subheader("Calculator Steps")
                for s in rpt['steps']:
                    st.write(s['calculator'], s['output'])
            st.subheader("Calculator Steps")
            for s in rpt['steps']:
                st.write(s['calculator'], s['output'])

    else:  # Category report
        cat_names = {c.name: c.id for c in categories}
        sel = st.selectbox("Category", list(cat_names.keys()))
        sel_id = cat_names[sel]

        def agg_category_summary(cat_id, trans, cats, acc=None):
            total = 0
            count = 0
            for t in trans:
                if _get_catid(t) == cat_id:
                    count += 1
                    amt = _get_amount(t) or 0
                    if amt < 0:
                        total += -float(amt)
            return {"count": count, "total_expense": total}

        rsvc = ReportService(aggregators=[agg_category_summary])
        cr = rsvc.category_report(sel_id, st.session_state.tx_transactions, categories)

        # show metrics and a monthly breakdown
        st.header(sel)
        col_a, col_b, col_c = st.columns([2, 1, 1])
        col_a.metric("Transactions", cr['result'].get('count', 0))
        col_b.metric("Total Expense", f"{cr['result'].get('total_expense', 0):,.0f} KZT")
        # monthly breakdown
        cat_trans = [t for t in st.session_state.tx_transactions if _get_catid(t) == sel_id]
        if cat_trans:
            dates = pd.to_datetime([str(_get_date(t)) for t in cat_trans], errors='coerce')
            dfc = pd.DataFrame({"date": dates, "amount": [_get_amount(t) for t in cat_trans]})
            dfc = dfc.dropna(subset=['date'])
            if not dfc.empty:
                monthly = dfc.set_index('date').resample('M')['amount'].sum().abs()
                df_month = pd.DataFrame({"month": [d.strftime('%Y-%m') for d in monthly.index], "amount": monthly.values})
                figm = px.bar(df_month, x='month', y='amount', title=f"Monthly spending for {sel}", template='plotly_dark')
                st.plotly_chart(figm, use_container_width=True)
                st.table(df_month)
        else:
            st.info("No transactions for this category yet")

        if show_steps:
            with st.expander("Intermediate steps", expanded=False):
                for s in cr['steps']:
                    st.write(s)
                st.write(cr['result'])

elif menu == "📊 Analytics":
    from core.lazy import iter_transactions, lazy_top_categories

    st.title("📊 Analytics")

    # Category tree and totals
    st.subheader("Category structure and totals")
    cat_names = {c.name: c.id for c in categories}
    selected_name = st.selectbox("Category", list(cat_names.keys()))
    selected_id = cat_names[selected_name]
    subs = flatten_categories(categories, selected_id)
    total = sum_expenses_recursive(categories, st.session_state.tx_transactions, selected_id)
    col_left, col_right = st.columns([2, 3])
    with col_left:
        st.write("Subcategories:")
        for c in subs:
            st.write(f"- {c.name}")
        st.metric("Total Expenses (incl. subcategories)", f"{abs(total):,} KZT")
    with col_right:
        # small pie of subcategory totals
        pie_data = []
        for c in subs:
            amt = sum_expenses_recursive(categories, st.session_state.tx_transactions, c.id)
            if amt != 0:
                pie_data.append({"name": c.name, "value": abs(amt)})
        if pie_data:
            dfi = pd.DataFrame(pie_data)
            figp = px.pie(dfi, values='value', names='name', title='Subcategory distribution')
            st.plotly_chart(figp, use_container_width=True)
        else:
            st.info("No subcategory expense data")

    st.divider()

    # Forecast
    st.subheader("Expense forecast (6 months)")
    start_t = time.time()
    _ = forecast_expenses(selected_id, tuple(st.session_state.tx_transactions), 6)
    uncached_time = (time.time() - start_t) * 1000
    start_t = time.time()
    forecast_value = forecast_expenses(selected_id, tuple(st.session_state.tx_transactions), 6)
    cached_time = (time.time() - start_t) * 1000
    st.metric("Forecasted Expenses", f"{forecast_value:,.0f} KZT")
    st.caption(f"⏱ Without cache: {uncached_time:.3f} ms | With cache: {cached_time:.3f} ms")

    st.divider()

    # Top-k categories
    st.subheader("Top expense categories")
    k = st.number_input("Show top-K categories:", min_value=1, max_value=20, value=5, key="top_k_analytics")
    if st.button("Calculate Top Categories", key="btn_top_k_analytics"):
        expense_gen = iter_transactions(st.session_state.tx_transactions, lambda t: getattr(t, 'amount', t.get('amount') if isinstance(t, dict) else 0) < 0)
        top_cats = list(lazy_top_categories(expense_gen, categories, k))
        if top_cats:
            df_top = pd.DataFrame([{"Category": n, "Amount": v} for n, v in top_cats])
            fig_top = px.bar(df_top, x='Category', y='Amount', title='Top expense categories', template='plotly_dark')
            st.plotly_chart(fig_top, use_container_width=True)
            st.table(df_top)
        else:
            st.info("No data to analyze")
