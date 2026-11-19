import streamlit as st
import mysql.connector
import pandas as pd
import bcrypt

st.set_page_config(page_title="Sales Intelligence Hub", page_icon="📊", layout="wide")
st.title("Sales Intelligence Hub")

def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"]
    )

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:
    st.subheader("User Login")
    email = st.text_input("Email", key="login_email").strip().lower()
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_button"):
        if not email or not password:
            st.warning("Enter email and password.")
        else:
            login_conn = None
            cur = None
            try:
                login_conn = get_connection()
                cur = login_conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM users WHERE LOWER(TRIM(email))=%s", (email,))
                user = cur.fetchone()
                
                if user is None:
                    st.error("Email not found.")
                elif bcrypt.checkpw(password.encode(), user["password"].encode()):
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.session_state.email = user["email"]
                    st.session_state.branch_id = user["branch_id"]
                    st.session_state.role = user["role"]
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            except Exception as e:
                st.error(f"Login error: {e}")
            finally:
                if cur is not None:
                    cur.close()
                if login_conn is not None and login_conn.is_connected():
                    login_conn.close()

# ---------------- DASHBOARD ----------------
if st.session_state.logged_in:
    st.sidebar.write("User:", st.session_state.username)
    st.sidebar.write("Role:", st.session_state.role)
    st.sidebar.write("Email:", st.session_state.email)
    if st.sidebar.button("Logout", key="logout_button"):
        for key in ["logged_in", "username", "email", "branch_id", "role"]:
            st.session_state.pop(key, None)
        st.rerun()

    conn = None
    try:
        conn = get_connection()
        role = st.session_state.role
        branch_id = st.session_state.branch_id
        branches = pd.read_sql(
            "SELECT branch_id, branch_name FROM branches ORDER BY branch_name", conn
        )

        # Every Admin query is restricted to their assigned branch.
        if role == "Super Admin":
            sales = pd.read_sql(
                "SELECT * FROM customer_sales ORDER BY sale_id DESC", conn
            )
        else:
            sales = pd.read_sql(
                "SELECT * FROM customer_sales WHERE branch_id=%s ORDER BY sale_id DESC",
                conn, params=(branch_id,)
            )
            
        # 1. Customer Sales Data and branch filter
        st.header("1. Customer Sales Data")
        if role == "Super Admin":
            branch_choice = st.selectbox(
                "Filter by Branch",
                ["All Branches"] + branches.branch_name.tolist(),
                key="sales_branch_filter"
            )
            if branch_choice != "All Branches":
                chosen_id = int(branches.loc[
                    branches.branch_name == branch_choice, "branch_id"
                ].iloc[0])
                view_sales = sales[sales.branch_id == chosen_id].copy()
            else:
                view_sales = sales.copy()
        else:
            view_sales = sales.copy()
            st.caption("You can view only your assigned branch.")

        st.dataframe(
            view_sales.drop(columns=["branch_id"], errors="ignore"),
            use_container_width=True, hide_index=True
        )

        # 2. Sales Summary - follows selected branch filter
        st.header("2. Sales Summary")
        a = float(view_sales.gross_sales.sum()) if not view_sales.empty else 0
        b = float(view_sales.received_amount.sum()) if not view_sales.empty else 0
        c = float(view_sales.pending_amount.sum()) if not view_sales.empty else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Sales", f"₹{a:,.2f}")
        m2.metric("Received Amount", f"₹{b:,.2f}")
        m3.metric("Pending Amount", f"₹{c:,.2f}")

        # 3. Add New Sales Entry
        st.header("3. Add New Sales Entry")
        with st.form("sales_entry_form", clear_on_submit=True):
            if role == "Super Admin":
                branch_choice_new = st.selectbox(
                    "Select Branch", branches.branch_name.tolist(),
                    key="new_sale_branch"
                )
                new_branch_id = int(branches.loc[
                    branches.branch_name == branch_choice_new, "branch_id"
                ].iloc[0])
            else:
                new_branch_id = int(branch_id)
                branch_name = branches.loc[
                    branches.branch_id == branch_id, "branch_name"
                ].iloc[0]
                st.write("Assigned Branch:", branch_name)
            sale_date = st.date_input("Sale Date", key="sale_date_input")
            customer = st.text_input("Customer Name")
            mobile = st.text_input("Mobile Number")
            product = st.selectbox("Product", ["DS", "DA", "BA", "FSD", "Laptop"])
            gross = st.number_input(
                "Gross Sales Amount", min_value=1.0, value=10000.0, step=1000.0
            )
            add_sale = st.form_submit_button("Add Sale")
        if add_sale:
            if not customer.strip() or not mobile.strip():
                st.warning("Enter customer name and mobile number.")
            else:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO customer_sales
                    (branch_id, `date`, name, mobile_number, product_name,
                     gross_sales, received_amount, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (new_branch_id, sale_date, customer.strip(), mobile.strip(),
                     product, gross, 0.00, "open")
                )
                conn.commit()
                cur.close()
                st.success("Sale added.")
                st.rerun()

        # 4. Add Payment Splits (existing AFTER INSERT trigger updates received_amount)
        st.header("4. Add Payment Splits")
        if role == "Super Admin":\
            pay_sales = pd.read_sql(
                """SELECT sale_id,name,product_name,gross_sales,pending_amount
                FROM customer_sales WHERE pending_amount>0 ORDER BY sale_id""", conn
            )
        else:
            pay_sales = pd.read_sql(
                """SELECT sale_id,name,product_name,gross_sales,pending_amount
                FROM customer_sales WHERE branch_id=%s AND pending_amount>0
                ORDER BY sale_id""", conn, params=(branch_id,)
            )
        if not pay_sales.empty:
            with st.form("payment_form", clear_on_submit=True):
                sale_id = st.selectbox("Sale ID", pay_sales.sale_id.tolist())
                sale_row = pay_sales[pay_sales.sale_id == sale_id].iloc[0]
                st.write("Customer:", sale_row["name"])
                st.write("Product:", sale_row["product_name"])
                pending = float(sale_row["pending_amount"])
                st.write(f"Pending Amount: ₹{pending:,.2f}")
                pay_date = st.date_input("Payment Date", key="payment_date_input")
                amount = st.number_input(
                    "Amount Paid", min_value=0.01, max_value=pending,
                    value=min(1000.0, pending), step=100.0
                )
                method = st.selectbox(
                    "Payment Method", ["Cash", "UPI", "Card", "Bank Transfer"]
                )
                add_payment = st.form_submit_button("Add Payment")
            if add_payment:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO payment_splits
                    (sale_id,payment_date,amount_paid,payment_method)
                    VALUES (%s,%s,%s,%s)""",
                    (int(sale_id), pay_date, amount, method)
                )
                conn.commit()
                cur.close()
                st.success("Payment added.")
                st.rerun()
        else:
            st.info("No pending sales available for payment.")

        # 5. Payment History
        st.header("5. Payment History")
        history_sql = """SELECT p.payment_id,p.sale_id,cs.name AS customer_name,
            cs.product_name,p.payment_date,p.amount_paid,p.payment_method
            FROM payment_splits p JOIN customer_sales cs ON p.sale_id=cs.sale_id"""
        if role != "Super Admin":
            history_sql += " WHERE cs.branch_id=%s"
            history = pd.read_sql(
                history_sql + " ORDER BY p.payment_date DESC",
                conn, params=(branch_id,)
            )
        else:
            history = pd.read_sql(
                history_sql + " ORDER BY p.payment_date DESC", conn
            )
        st.dataframe(history, use_container_width=True, hide_index=True)

        # 6. Date-wise Sales Filter
        st.header("6. Date-wise Sales Filter")
        chosen_date = st.date_input("Select Sales Date", key="date_filter_input")
        date_sql = "SELECT * FROM customer_sales WHERE `date`=%s"
        date_params = [chosen_date]
        if role != "Super Admin":
            date_sql += " AND branch_id=%s"
            date_params.append(branch_id)
        date_df = pd.read_sql(date_sql, conn, params=tuple(date_params))
        st.dataframe(date_df, use_container_width=True, hide_index=True)
        st.metric(
            "Selected Date Total Sales",
            f"₹{float(date_df.gross_sales.sum()) if not date_df.empty else 0:,.2f}"
        )

        # 7. Pending Payments Report
        st.header("7. Pending Payments Report")
        pending_sql = """SELECT sale_id,name AS customer_name,mobile_number,
            `date` AS sale_date,gross_sales,received_amount,pending_amount,status
            FROM customer_sales WHERE pending_amount>0"""
        pending_params = []
        if role != "Super Admin":
            pending_sql += " AND branch_id=%s"
            pending_params.append(branch_id)
        pending_sql += " ORDER BY pending_amount DESC"
        pending_df = pd.read_sql(
            pending_sql, conn,
            params=tuple(pending_params) if pending_params else None
        )
        st.dataframe(pending_df, use_container_width=True, hide_index=True)
        st.metric(
            "Total Pending Payments",
            f"₹{float(pending_df.pending_amount.sum()) if not pending_df.empty else 0:,.2f}"
        )

        # 8. Open / Close Status Management
        st.header("8. Sales Status Management")
        if role == "Super Admin":
            status_df = pd.read_sql(
                "SELECT sale_id,name,pending_amount,status FROM customer_sales", conn
            )
        else:
            status_df = pd.read_sql(
                """SELECT sale_id,name,pending_amount,status FROM customer_sales
                WHERE branch_id=%s""", conn, params=(branch_id,)
            )
        st.dataframe(status_df, use_container_width=True, hide_index=True)
        if not status_df.empty:
            chosen_status_id = st.selectbox(
                "Select Sale ID", status_df.sale_id.tolist(), key="status_sale"
            )
            record = status_df[status_df.sale_id == chosen_status_id].iloc[0]
            if float(record.pending_amount) > 0:
                st.warning("This sale has a pending amount and cannot be closed.")
            else:
                new_status = st.selectbox(
                    "New Status", ["open", "close"],
                    index=0 if record.status == "open" else 1,
                    key="status_choice"
                )
                if st.button("Update Sales Status", key="update_status"):
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE customer_sales SET status=%s WHERE sale_id=%s",
                        (new_status, int(chosen_status_id))
                    )
                    conn.commit()
                    cur.close()
                    st.success("Status updated.")
                    st.rerun()

        # 9. Payment Method Summary
        st.header("9. Payment Method Summary")
        method_sql = """SELECT p.payment_method,SUM(p.amount_paid) AS total_received,
            COUNT(*) AS payment_count FROM payment_splits p
            JOIN customer_sales cs ON p.sale_id=cs.sale_id"""
        method_params = []
        if role != "Super Admin":
            method_sql += " WHERE cs.branch_id=%s"
            method_params.append(branch_id)
        method_sql += " GROUP BY p.payment_method ORDER BY total_received DESC"
        method_df = pd.read_sql(
            method_sql, conn,
            params=tuple(method_params) if method_params else None
        )
        st.dataframe(method_df, use_container_width=True, hide_index=True)
        if not method_df.empty:
            st.bar_chart(method_df.set_index("payment_method")["total_received"])

        # 10. Charts and Business Insights
        st.header("10. Charts and Business Insights")
        if not view_sales.empty:
            chart_sales = view_sales.merge(branches, on="branch_id", how="left")
            by_branch = chart_sales.groupby("branch_name")["gross_sales"].sum()
            by_product = view_sales.groupby("product_name")["gross_sales"].sum()
            st.subheader("Sales by Branch")
            st.bar_chart(by_branch)
            st.subheader("Sales by Product")
            st.bar_chart(by_product)
            st.subheader("Received vs Pending")
            st.bar_chart(pd.Series({
                "Received": float(view_sales.received_amount.sum()),
                "Pending": float(view_sales.pending_amount.sum())
            }))
            if not by_product.empty:
                top_product = by_product.idxmax()
                st.write(
                    f"Business Insight: {top_product} has the highest sales "
                    f"in this selection (₹{float(by_product.max()):,.2f})."
                )
        else:
            st.info("No sales data for charts.")

        # 11. 18 Analytical SQL Reports
        st.header("11. Analytical SQL Reports")
        reports = {
            "1. Total Sales by Branch": (
                """SELECT b.branch_name,SUM(c.gross_sales) AS total_sales
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                WHERE c.branch_id=%s GROUP BY b.branch_name""",
                """SELECT b.branch_name,SUM(c.gross_sales) AS total_sales
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                GROUP BY b.branch_name"""),
            "2. Total Received by Branch": (
                """SELECT b.branch_name,SUM(c.received_amount) AS total_received
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                WHERE c.branch_id=%s GROUP BY b.branch_name""",
                """SELECT b.branch_name,SUM(c.received_amount) AS total_received
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                GROUP BY b.branch_name"""),
            "3. Pending by Branch": (
                """SELECT b.branch_name,SUM(c.pending_amount) AS total_pending
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                WHERE c.branch_id=%s GROUP BY b.branch_name""",
                """SELECT b.branch_name,SUM(c.pending_amount) AS total_pending
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                GROUP BY b.branch_name"""),
            "4. Total Sales by Product": (
                "SELECT product_name,SUM(gross_sales) AS total_sales FROM customer_sales WHERE branch_id=%s GROUP BY product_name",
                "SELECT product_name,SUM(gross_sales) AS total_sales FROM customer_sales GROUP BY product_name"),
            "5. Number of Sales by Branch": (
                """SELECT b.branch_name,COUNT(*) AS sale_count FROM branches b
                JOIN customer_sales c ON b.branch_id=c.branch_id
                WHERE c.branch_id=%s GROUP BY b.branch_name""",
                """SELECT b.branch_name,COUNT(*) AS sale_count FROM branches b
                JOIN customer_sales c ON b.branch_id=c.branch_id GROUP BY b.branch_name"""),
            "6. Number of Sales by Product": (
                "SELECT product_name,COUNT(*) AS sale_count FROM customer_sales WHERE branch_id=%s GROUP BY product_name",
                "SELECT product_name,COUNT(*) AS sale_count FROM customer_sales GROUP BY product_name"),
            "7. Sales by Branch and Product": (
                """SELECT b.branch_name,c.product_name,SUM(c.gross_sales) AS total_sales
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                WHERE c.branch_id=%s GROUP BY b.branch_name,c.product_name""",
                """SELECT b.branch_name,c.product_name,SUM(c.gross_sales) AS total_sales
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                GROUP BY b.branch_name,c.product_name"""),
            "8. Highest Sale": (
                "SELECT MAX(gross_sales) AS highest_sale FROM customer_sales WHERE branch_id=%s",
                "SELECT MAX(gross_sales) AS highest_sale FROM customer_sales"),
            "9. Lowest Sale": (
                "SELECT MIN(gross_sales) AS lowest_sale FROM customer_sales WHERE branch_id=%s",
                "SELECT MIN(gross_sales) AS lowest_sale FROM customer_sales"),
            "10. Average Sale": (
                "SELECT AVG(gross_sales) AS average_sale FROM customer_sales WHERE branch_id=%s",
                "SELECT AVG(gross_sales) AS average_sale FROM customer_sales"),
            "11. Top 5 Sales": (
                "SELECT sale_id,name,product_name,gross_sales FROM customer_sales WHERE branch_id=%s ORDER BY gross_sales DESC LIMIT 5",
                "SELECT sale_id,name,product_name,gross_sales FROM customer_sales ORDER BY gross_sales DESC LIMIT 5"),
            "12. Sales by Date": (
                "SELECT `date`,SUM(gross_sales) AS daily_sales FROM customer_sales WHERE branch_id=%s GROUP BY `date` ORDER BY `date`",
                "SELECT `date`,SUM(gross_sales) AS daily_sales FROM customer_sales GROUP BY `date` ORDER BY `date`"),
            "13. Payment Totals by Method": (
                """SELECT p.payment_method,SUM(p.amount_paid) AS total_paid
                FROM payment_splits p JOIN customer_sales c ON p.sale_id=c.sale_id
                WHERE c.branch_id=%s GROUP BY p.payment_method""",
                "SELECT payment_method,SUM(amount_paid) AS total_paid FROM payment_splits GROUP BY payment_method"),
            "14. Payment Count by Method": (
                """SELECT p.payment_method,COUNT(*) AS payment_count
                FROM payment_splits p JOIN customer_sales c ON p.sale_id=c.sale_id
                WHERE c.branch_id=%s GROUP BY p.payment_method""",
                "SELECT payment_method,COUNT(*) AS payment_count FROM payment_splits GROUP BY payment_method"),
            "15. Fully Paid Sales": (
                "SELECT sale_id,name,gross_sales,received_amount FROM customer_sales WHERE branch_id=%s AND pending_amount=0",
                "SELECT sale_id,name,gross_sales,received_amount FROM customer_sales WHERE pending_amount=0"),
            "16. Open Sales with Pending": (
                "SELECT sale_id,name,pending_amount FROM customer_sales WHERE branch_id=%s AND status='open' AND pending_amount>0",
                "SELECT sale_id,name,pending_amount FROM customer_sales WHERE status='open' AND pending_amount>0"),
            "17. Average Sale by Branch": (
                """SELECT b.branch_name,AVG(c.gross_sales) AS average_sale
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                WHERE c.branch_id=%s GROUP BY b.branch_name""",
                """SELECT b.branch_name,AVG(c.gross_sales) AS average_sale
                FROM branches b JOIN customer_sales c ON b.branch_id=c.branch_id
                GROUP BY b.branch_name"""),
            "18. Customer-wise Sales": (
                "SELECT name,SUM(gross_sales) AS customer_sales FROM customer_sales WHERE branch_id=%s GROUP BY name ORDER BY customer_sales DESC",
                "SELECT name,SUM(gross_sales) AS customer_sales FROM customer_sales GROUP BY name ORDER BY customer_sales DESC")
        }
        report_name = st.selectbox("Select Report", list(reports.keys()))
        admin_sql, super_sql = reports[report_name]
        if role == "Super Admin":
            report_df = pd.read_sql(super_sql, conn)
        else:
            report_df = pd.read_sql(admin_sql, conn, params=(branch_id,))
        st.dataframe(report_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Dashboard error: {e}")
    finally:
        if conn is not None and conn.is_connected():
            conn.close()
        